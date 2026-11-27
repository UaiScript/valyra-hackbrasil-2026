"""Integração do serviço IA com Finance real e cliente LLM simulado."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from valyra.ai.schemas import ExplainRequest, LLMPayload
from valyra.ai.service import explain_for_account
from valyra.core.errors import AppError

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
