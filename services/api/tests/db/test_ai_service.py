"""Integração do serviço IA com Finance real e cliente LLM simulado."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from valyra.ai.schemas import ExplainRequest, LLMPayload
from valyra.ai.service import explain_for_account
from valyra.core import clock as business_clock
from valyra.core.errors import AppError
from valyra.finance.models import Budget, Category, ImportBatch

pytestmark = pytest.mark.postgres


def current_cutoff(account, *transactions):
    # Independente do relógio da máquina: o corte cobre as fixtures e seus timestamps reais.
    values = [datetime(2026, 11, 17, 12, tzinfo=UTC), account.updated_at]
    values.extend(row.updated_at for row in transactions)
    return max(values) + timedelta(seconds=1)


def reference_reply(sent):
    item = next(e for e in sent.context_data.evidences if e.basis == "reference")
    return LLMPayload(
        answer=f"Saldo de referência {item.display_value}.",
        evidence_ids=[item.evidence_id],
        uncertainty="alta",
        limitations=[],
    )


def test_ligacao_real_finance_autoriza_ler_contexto_e_nao_faz_commit(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    tx = insert_transaction()
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, tx)
    client = Mock(side_effect=reference_reply)
    commit = Mock(side_effect=AssertionError("Serviço IA não controla commit"))
    monkeypatch.setattr(db_session, "commit", commit)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    sent = client.call_args.args[0]
    assert sent.context_data.account_id == account.id
    assert [e.source.record_id for e in sent.context_data.evidences] == [account.id, tx.id]
    assert sent.context_data.evidences[1].value.amount_cents == tx.amount_cents
    assert response.evidences[0].value.amount_cents == account.balance_cents
    commit.assert_not_called()


@pytest.mark.parametrize("target", ["other_user", "missing_account"])
def test_conta_alheia_e_inexistente_sao_indistinguiveis_antes_de_qualquer_chamada(
    db_session, reference_rows, target
):
    account, user = reference_rows["account"], reference_rows["user"]
    user_id = uuid4() if target == "other_user" else user.id
    account_id = account.id if target == "other_user" else uuid4()
    client, provider = Mock(), Mock()
    with pytest.raises(AppError) as caught:
        explain_for_account(
            db_session,
            user_id,
            ExplainRequest(question="Explique", account_id=account_id),
            client=client,
            context_provider=provider,
        )
    assert (caught.value.code, caught.value.status_code, caught.value.message) == (
        "ACCOUNT_NOT_FOUND",
        404,
        "Conta não encontrada",
    )
    client.assert_not_called()
    provider.assert_not_called()


def test_bigint_valido_no_finance_mas_inseguro_no_json_nao_vaza_ou_vira_zero(
    db_session, reference_rows
):
    account, user = reference_rows["account"], reference_rows["user"]
    account.balance_cents = 2**63 - 1
    db_session.flush()
    cut = current_cutoff(account)
    client = Mock(side_effect=AssertionError("Sem evidência elegível não chamar LLM"))
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    assert response.evidences == [] and response.uncertainty == "alta"
    assert any("precisão" in text for text in response.limitations)
    assert account.balance_cents == 2**63 - 1
    client.assert_not_called()


def test_recorte_real_declara_parcialidade_sem_calcular_resumo(
    db_session, reference_rows, insert_transaction
):
    rows = [insert_transaction() for _ in range(21)]
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, *rows)
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    evidences = client.call_args.args[0].context_data.evidences
    assert len(evidences) == 21  # Uma referência e o recorte operacional de movimentações.
    assert {e.metric_key for e in evidences} == {
        "finance.account.reference_balance",
        "finance.transaction.amount",
    }
    assert any("Histórico parcial" in text for text in response.limitations)


def test_lote_concluido_entrega_calculos_finance_citaveis_sem_o_llm_calcular(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    account, user = reference_rows["account"], reference_rows["user"]
    batch, category = reference_rows["batch"], reference_rows["category"]
    rows = [
        insert_transaction(date=date(2026, 11, 3), amount_cents=-8990),
        insert_transaction(date=date(2026, 10, 10), amount_cents=-4000),
    ]
    db_session.add(Budget(user_id=user.id, category_id=category.id, limit_cents=10000))
    batch.status, batch.rows_total, batch.rows_imported = "completed", 2, 2
    batch.completed_at = batch.created_at
    db_session.flush()
    cut = current_cutoff(account, *rows)
    today = cut.astimezone(business_clock.BUSINESS_TIMEZONE).date()
    monkeypatch.setattr(business_clock, "get_today", lambda: today)

    def reply(sent):
        items = {e.evidence_id: e for e in sent.context_data.evidences}
        spent = items[f"budget_spent_{category.id.hex}"]
        return LLMPayload(
            answer=f"Você gastou {spent.display_value} em Outros neste mês.",
            evidence_ids=[spent.evidence_id],
            uncertainty="baixa",
            limitations=[],
        )

    client = Mock(side_effect=reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Como está meu orçamento?", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    sent = client.call_args.args[0].context_data
    items = {e.evidence_id: e for e in sent.evidences}
    # Valores vêm do Finance: o LLM só recebe resultados prontos para citar.
    assert items["month_expenses"].value.amount_cents == -8990
    assert items["prev_month_expenses"].value.amount_cents == -4000
    assert items[f"budget_limit_{category.id.hex}"].value.amount_cents == 10000
    assert (
        items[f"budget_status_{category.id.hex}"].value.value_text == "em atenção, perto do limite"
    )
    assert items["projection_end_balance"].basis == "projected"
    assert items["projection_end_balance"].period.start > today
    calc = items["month_expenses"].source
    assert calc.kind == "calculation" and calc.input_scope.import_batch_ids == [batch.id]
    assert items[f"tx_{rows[0].id.hex}"].label == "Movimentação importada · Outros"
    assert not any("resumo, orçamento e projeção" in text for text in response.limitations)
    assert response.evidences[0].value.amount_cents == 8990


def test_data_de_negocio_posterior_ao_corte_omite_calculos(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    account, user, batch = (reference_rows[k] for k in ("account", "user", "batch"))
    tx = insert_transaction()
    batch.status, batch.rows_total, batch.rows_imported = "completed", 1, 1
    batch.completed_at = batch.created_at
    db_session.flush()
    cut = current_cutoff(account, tx)
    future = cut.astimezone(business_clock.BUSINESS_TIMEZONE).date() + timedelta(days=5)
    monkeypatch.setattr(business_clock, "get_today", lambda: future)
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    keys = {e.metric_key for e in client.call_args.args[0].context_data.evidences}
    assert keys == {"finance.account.reference_balance", "finance.transaction.amount"}
    assert any("posterior ao corte" in text for text in response.limitations)


def _complete(batch, rows):
    batch.status, batch.rows_total, batch.rows_imported = "completed", rows, rows
    batch.completed_at = batch.created_at


def test_lote_concluido_depois_do_corte_omite_todos_os_calculos(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    account, user, batch = (reference_rows[k] for k in ("account", "user", "batch"))
    tx = insert_transaction()
    _complete(batch, 1)
    db_session.flush()
    cut = current_cutoff(account, tx)
    late = ImportBatch(account_id=account.id, file_name="depois.csv", status="completed")
    late.rows_total = late.rows_imported = 0
    late.completed_at = cut + timedelta(minutes=5)
    db_session.add(late)
    db_session.flush()
    monkeypatch.setattr(
        business_clock, "get_today", lambda: cut.astimezone(business_clock.BUSINESS_TIMEZONE).date()
    )
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    keys = {e.metric_key for e in client.call_args.args[0].context_data.evidences}
    # Os services leem o estado atual: com mudança após o corte, nenhum total é confiável.
    assert keys == {"finance.account.reference_balance", "finance.transaction.amount"}
    assert any("depois do corte" in text for text in response.limitations)


def test_demo_today_anterior_ao_corte_so_projeta_dias_futuros(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    account, user, batch = (reference_rows[k] for k in ("account", "user", "batch"))
    rows = [insert_transaction(date=date(2026, 11, d), amount_cents=-1000) for d in (2, 3)]
    _complete(batch, 2)
    db_session.flush()
    cut = current_cutoff(account, *rows)
    cut_day = cut.astimezone(business_clock.BUSINESS_TIMEZONE).date()
    monkeypatch.setattr(business_clock, "get_today", lambda: cut_day - timedelta(days=3))
    client = Mock(side_effect=reference_reply)
    explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    items = {e.evidence_id: e for e in client.call_args.args[0].context_data.evidences}
    projected = [e for e in items.values() if e.basis == "projected"]
    assert {e.evidence_id for e in projected} == {
        "projection_end_balance",
        "projection_min_balance",
        "projection_variable_daily",
    }
    assert all(e.period.start > cut_day for e in projected)


def test_orcamento_com_muitas_categorias_prioriza_pressao_e_respeita_teto(
    db_session, reference_rows, insert_transaction, monkeypatch
):
    account, user, batch = (reference_rows[k] for k in ("account", "user", "batch"))
    categories = [
        Category(slug=f"cat-{n}", name=f"Categoria {chr(65 + n)}", kind="expense")
        for n in range(12)
    ]
    db_session.add_all(categories)
    db_session.flush()
    rows = [
        insert_transaction(category_id=c.id, predicted_category_id=c.id, amount_cents=-5000)
        for c in categories
    ]
    for n, category in enumerate(categories):
        # As duas primeiras estouram o teto; as demais ficam folgadas.
        limit = 1000 if n < 2 else 100000
        db_session.add(Budget(user_id=user.id, category_id=category.id, limit_cents=limit))
    _complete(batch, len(rows))
    db_session.flush()
    cut = current_cutoff(account, *rows)
    monkeypatch.setattr(
        business_clock, "get_today", lambda: cut.astimezone(business_clock.BUSINESS_TIMEZONE).date()
    )
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="Explique", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    evidences = client.call_args.args[0].context_data.evidences
    statuses = [e for e in evidences if e.metric_key == "finance.budget.status"]
    assert len(statuses) == 8 and len(evidences) <= 100
    over = {f"budget_status_{c.id.hex}" for c in categories[:2]}
    assert over <= {e.evidence_id for e in statuses}
    assert any("Orçamento parcial" in text for text in response.limitations)


def test_sinais_alpha_publicados_ate_o_corte_viram_evidencias_citaveis(
    db_session, reference_rows, insert_transaction
):
    from decimal import Decimal

    from valyra.alpha import service as alpha_service
    from valyra.alpha.domain import SGS_SERIES

    selic = SGS_SERIES[0]
    tx = insert_transaction()
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, tx)
    url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
    alpha_service.record_observation(
        db_session, selic, date(2026, 11, 3), Decimal("15"),
        ingested_at=cut - timedelta(days=1), source_url=url,
    )  # fmt: skip
    # Coletada depois do corte: não pode chegar ao LLM (regra de data leakage).
    alpha_service.record_observation(
        db_session, selic, date(2026, 11, 3), Decimal("14.75"),
        ingested_at=cut + timedelta(days=1), source_url=url,
    )  # fmt: skip
    db_session.flush()
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="E a Selic?", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    sent = client.call_args.args[0].context_data
    [alpha] = [e for e in sent.evidences if e.source.kind == "alpha_signal"]
    assert alpha.value.value_decimal == "15" and alpha.value.unit == "%"
    assert alpha.source.published_at <= cut
    assert any("não demonstra causa" in text for text in response.limitations)


def test_manchetes_da_semana_viram_evidencia_textual_com_fonte(
    db_session, reference_rows, insert_transaction
):
    from valyra.alpha import news_service
    from valyra.alpha.news import FeedItem

    tx = insert_transaction()
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, tx)
    link = "https://agenciabrasil.ebc.com.br/economia/noticia/teste-gasolina"
    news_service.record_news(
        db_session,
        FeedItem("agencia-brasil", "Gasolina sobe nos postos", "", link, cut - timedelta(days=1)),
        ingested_at=cut - timedelta(hours=12),
    )
    # Publicada depois do corte: não pode chegar ao LLM.
    news_service.record_news(
        db_session,
        FeedItem("agencia-brasil", "Selic muda", "", link + "-2", cut + timedelta(hours=1)),
        ingested_at=cut + timedelta(hours=2),
    )
    db_session.flush()
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="O que saiu na semana?", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    sent = client.call_args.args[0].context_data
    [news] = [e for e in sent.evidences if e.metric_key.startswith("alpha.news.")]
    assert news.metric_key == "alpha.news.combustiveis"
    assert news.value.value_text == "Gasolina sobe nos postos"
    assert str(news.source.source_url) == link
    assert any("news_theme_v3" in text for text in response.limitations)


def test_previsao_com_dados_coletados_vira_evidencia_projetada_citavel(
    db_session, reference_rows, insert_transaction
):
    from decimal import Decimal

    from valyra.alpha import service as alpha_service
    from valyra.alpha.domain import SGS_SERIES
    from valyra.alpha.forecast import add_months

    tx = insert_transaction()
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, tx)
    for i in range(36):
        alpha_service.record_observation(
            db_session, SGS_SERIES[2], add_months(date(2023, 9, 1), i),
            Decimal("0.30") + Decimal(i % 5) / 10, ingested_at=cut - timedelta(days=2),
            source_url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados", backfill=True,
        )  # fmt: skip
    db_session.flush()
    client = Mock(side_effect=reference_reply)
    response = explain_for_account(
        db_session,
        user.id,
        ExplainRequest(question="E a inflação?", account_id=account.id),
        client=client,
        clock=lambda: cut,
    )
    sent = client.call_args.args[0].context_data
    by_id = {e.evidence_id: e for e in sent.evidences}
    central = by_id["forecast_ipca_12m_p50"]
    assert central.basis == "projected" and central.source.module == "alpha"
    assert central.period.start > cut.date() and central.value.unit == "%"
    assert {"forecast_ipca_12m_p10", "forecast_ipca_12m_p90", "forecast_ipca_12m_chance"} <= set(
        by_id
    )
    # Selic e ações estão sem histórico: a reserva sintética nunca chega ao LLM.
    assert not any(key.startswith("forecast_selic") for key in by_id)
    assert any("reserva sintéticas" in text for text in response.limitations)
