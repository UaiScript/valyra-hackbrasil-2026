"""Orquestração e adaptador Finance com contexto, cliente e leitura substituídos."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from tests.ai.factories import (
    ACCOUNT_ID,
    AS_OF,
    BUILT_AT,
    context_data,
    crowded_context,
    money_evidence,
)
from valyra.ai import service
from valyra.ai.domain import EvidenceContextError, EvidenceReferenceError, UnsupportedClaimError
from valyra.ai.schemas import (
    EvidenceContext,
    EvidenceItem,
    ExplainRequest,
    HistoryMessage,
    LLMPayload,
)
from valyra.alpha.forecast_service import ProfileForecasts
from valyra.alpha.news_service import WeeklyReport
from valyra.alpha.service import Radar

EMPTY_RADAR = Radar(
    as_of=datetime(2026, 1, 1, tzinfo=UTC), indicators=[], signals=[], last_ingested_at=None
)
EMPTY_NEWS = WeeklyReport(
    as_of=datetime(2026, 1, 1, tzinfo=UTC),
    week_start=datetime(2025, 12, 25, tzinfo=UTC),
    themes=[],
    total=0,
    unmatched=0,
    sources=[],
    last_ingested_at=None,
)

NO_FORECASTS = ProfileForecasts(
    profile=None,
    as_of=datetime(2026, 1, 1, tzinfo=UTC),
    computed_at=datetime(2026, 1, 1, tzinfo=UTC),
    items=[],
)

CUT = datetime.fromisoformat(AS_OF.replace("Z", "+00:00"))
BUILT = datetime.fromisoformat(BUILT_AT.replace("Z", "+00:00"))
USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def request():
    return ExplainRequest(question="Explique meu contexto", account_id=ACCOUNT_ID)


def context(**changes):
    return EvidenceContext.model_validate(context_data(evidences=[money_evidence()]) | changes)


def reply(answer="Saldo de referência R$ 5.000,00.", ids=("e1",)):
    return LLMPayload(answer=answer, evidence_ids=list(ids), uncertainty="alta", limitations=[])


def transaction(**changes):
    return SimpleNamespace(
        **(
            {
                "id": uuid4(),
                "account_id": UUID(ACCOUNT_ID),
                "amount_cents": -8990,
                "date": date(2026, 11, 3),
                "updated_at": datetime(2026, 11, 3, tzinfo=UTC),
                "import_batch_id": uuid4(),
                "description": "DADO-RESERVADO",
            }
            | changes
        )
    )


@pytest.fixture
def finance(monkeypatch):
    account = SimpleNamespace(
        id=UUID(ACCOUNT_ID),
        balance_cents=500000,
        balance_as_of=date(2026, 11, 1),
        updated_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    get = Mock(return_value=account)
    transactions = Mock(return_value=([], 0))
    monkeypatch.setattr(service.finance_service, "get_account_for_user", get)
    monkeypatch.setattr(service.finance_service, "list_transactions", transactions)
    # Sem lote concluído, a montagem não calcula resumo, orçamento nem projeção.
    batches = Mock(return_value=[])
    monkeypatch.setattr(service.finance_service, "list_completed_import_batches", batches)
    monkeypatch.setattr(service.finance_service, "is_anomalous", Mock(return_value=False))
    # Radar vazio: sem coletas Alpha, o contexto declara a ausência como limitação.
    monkeypatch.setattr(service.alpha_service, "get_radar", Mock(return_value=EMPTY_RADAR))
    # Sem notícias coletadas: o relatório semanal não acrescenta evidências.
    monkeypatch.setattr(service.news_service, "get_weekly_report", Mock(return_value=EMPTY_NEWS))
    # Sem previsões (ADR-0016): estes testes não dependem da coleta Alpha.
    monkeypatch.setattr(service.forecast_service, "get_forecasts", Mock(return_value=NO_FORECASTS))
    return SimpleNamespace(
        account=account,
        get=get,
        transactions=transactions,
        batches=batches,
        session=Mock(spec=Session),
    )


def clock():
    return Mock(side_effect=[CUT, BUILT])


def test_cliente_nao_pode_adulterar_contexto_e_validar_seu_numero_inventado():
    original = context()
    before = original.model_dump_json()

    def malicious(sent):
        sent.context_data.evidences[0] = EvidenceItem.model_validate(
            money_evidence(value={"kind": "money", "amount_cents": 99900})
        )
        return reply("Saldo de referência R$ 999,00.")

    with pytest.raises(UnsupportedClaimError):
        service.explain_with_context(request(), original, client=malicious)
    assert original.model_dump_json() == before


def test_evidencia_omitida_pelo_tamanho_nao_pode_ser_citada_pelo_modelo():
    original = EvidenceContext.model_validate(crowded_context())
    omitted_id = original.evidences[-1].evidence_id

    def client(sent):
        assert omitted_id not in {item.evidence_id for item in sent.context_data.evidences}
        return reply("Informação sem suporte.", (omitted_id,))

    with pytest.raises(EvidenceReferenceError):
        service.explain_with_context(request(), original, client=client)


def test_historico_antigo_e_omitido_antes_das_evidencias_sem_cortar_mensagens():
    history = [HistoryMessage(role="user", content="á" * 4000) for _ in range(10)]

    def client(sent):
        assert 0 < len(sent.history) < len(history)
        assert all(message.content == "á" * 4000 for message in sent.history)
        assert sent.context_data.evidences == context().evidences
        return reply()

    response = service.explain_with_context(request(), context(), history=history, client=client)
    assert any("histórico de conversa" in text for text in response.limitations)
    assert len(history) == 10


def test_finance_autoriza_antes_de_produtor_substituivel_e_cliente(finance):
    order = []
    finance.get.side_effect = lambda *args: (order.append("authorize"), finance.account)[1]

    def provider(as_of):
        order.append("context")
        assert as_of == CUT
        return context()

    def client(sent):
        order.append("client")
        return reply()

    result = service.explain_for_account(
        finance.session, USER_ID, request(), client=client, context_provider=provider, clock=clock()
    )
    assert order == ["authorize", "context", "client"]
    assert result.evidences[0].value.amount_cents == 500000
    finance.get.assert_called_once_with(finance.session, USER_ID, UUID(ACCOUNT_ID))
    finance.transactions.assert_not_called()
    finance.session.commit.assert_not_called()
    finance.session.rollback.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        {"as_of": "2026-11-16T12:00:00Z"},
        {"built_at": "2026-11-18T12:00:00Z"},
        {"account_id": "00000000-0000-0000-0000-000000000999", "evidences": []},
    ],
)
def test_produtor_nao_pode_escolher_corte_ou_conta_diferente(finance, change):
    client = Mock()
    with pytest.raises(EvidenceContextError):
        service.explain_for_account(
            finance.session,
            USER_ID,
            request(),
            client=client,
            context_provider=lambda _: context(**change),
            clock=clock(),
        )
    client.assert_not_called()


def test_movimentacoes_usam_servico_publico_e_nao_enviam_descricao_ao_llm(finance):
    tx = transaction()
    finance.transactions.return_value = ([(tx, object())], 1)

    def client(sent):
        assert "DADO-RESERVADO" not in sent.model_dump_json()
        item = sent.context_data.evidences[1]
        assert item.source.record_id == tx.id
        assert item.source.import_batch_id == tx.import_batch_id
        assert item.value.amount_cents == -8990
        assert item.basis == "observed" and item.period.start == tx.date
        return reply("Movimentação importada: R$ -89,90.", (item.evidence_id,))

    response = service.explain_for_account(
        finance.session, USER_ID, request(), client=client, clock=clock()
    )
    assert response.evidences[0].value.amount_cents == tx.amount_cents


@pytest.mark.parametrize(
    "field,value",
    [("balance_cents", 2**63 - 1), ("balance_as_of", date(2026, 11, 18)), ("updated_at", BUILT)],
)
def test_saldo_incompativel_ou_futuro_e_omitido_com_limitacao(finance, field, value):
    setattr(finance.account, field, value)
    client = Mock()
    result = service.explain_for_account(
        finance.session, USER_ID, request(), client=client, clock=clock()
    )
    assert result.evidences == [] and result.uncertainty == "alta"
    assert result.limitations
    client.assert_not_called()


def test_saldo_zero_informado_e_diferente_de_ausencia_de_dados(finance):
    finance.account.balance_cents = 0
    client = Mock(return_value=reply("Referência de R$ 0,00.", ("account_reference_balance",)))
    result = service.explain_for_account(
        finance.session, USER_ID, request(), client=client, clock=clock()
    )
    assert result.evidences[0].value.amount_cents == 0
    client.assert_called_once()


def test_transacoes_inelegiveis_sao_omitidas_sem_zero_sintetico(finance):
    rows = [
        transaction(date=date(2026, 11, 18)),
        transaction(updated_at=BUILT),
        transaction(amount_cents=2**63 - 1),
    ]
    finance.transactions.return_value = ([(row, object()) for row in rows], 3)
    client = Mock(return_value=reply("Referência R$ 5.000,00.", ("account_reference_balance",)))
    result = service.explain_for_account(
        finance.session, USER_ID, request(), client=client, clock=clock()
    )
    assert len(client.call_args.args[0].context_data.evidences) == 1
    assert any("posteriores" in text for text in result.limitations)
    assert any("precisão" in text for text in result.limitations)
    assert len(result.evidences) == 1


def test_transacao_de_outra_conta_nao_pode_compor_contexto(finance):
    finance.transactions.return_value = ([(transaction(account_id=uuid4()), object())], 1)
    client = Mock()
    with pytest.raises(EvidenceContextError):
        service.explain_for_account(
            finance.session, USER_ID, request(), client=client, clock=clock()
        )
    client.assert_not_called()


@pytest.mark.parametrize("times", [[CUT.replace(tzinfo=None)], [CUT, CUT - timedelta(seconds=1)]])
def test_relogio_invalido_falha_sem_chamar_cliente(finance, times):
    client = Mock()
    with pytest.raises(EvidenceContextError):
        service.explain_for_account(
            finance.session, USER_ID, request(), client=client, clock=Mock(side_effect=times)
        )
    client.assert_not_called()
