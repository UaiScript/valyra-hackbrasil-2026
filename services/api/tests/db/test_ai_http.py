"""Jornada HTTP com conta/transação sintéticas no Finance real e LLM simulado."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from valyra.ai import llm_client
from valyra.ai.schemas import LLMPayload
from valyra.core.deps import get_current_user_id
from valyra.finance.models import Budget

pytestmark = pytest.mark.postgres
URL = "/api/v1/ai/explain"


@pytest.mark.parametrize("limit", [None, 1000, 10000])
def test_http_explica_limite_diario_do_finance_sem_confundir_ausencia_com_zero(
    client, app, db_session, reference_rows, insert_transaction, monkeypatch, limit
):
    from tests.db.test_ai_service import current_cutoff
    from valyra.ai import service
    from valyra.core import clock as business_clock

    account, user, batch, category = (
        reference_rows[k] for k in ("account", "user", "batch", "category")
    )
    tx = insert_transaction()
    batch.status, batch.rows_total, batch.rows_imported = "completed", 1, 1
    batch.completed_at = batch.created_at
    if limit is not None:
        db_session.add(Budget(user_id=user.id, category_id=category.id, limit_cents=limit))
    db_session.flush()
    cut = current_cutoff(account, tx)
    monkeypatch.setattr(
        business_clock, "get_today", lambda: cut.astimezone(business_clock.BUSINESS_TIMEZONE).date()
    )
    actual = service.explain_for_account
    monkeypatch.setattr(
        service,
        "explain_for_account",
        lambda session, uid, body: actual(session, uid, body, clock=lambda: cut),
    )
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    expected = client.get("/api/v1/finance/budgets").json()["daily_allowance_cents"]

    def reply(sent):
        items = {item.evidence_id: item for item in sent.context_data.evidences}
        if expected is None:
            assert "budget_daily_allowance" not in items
            return LLMPayload(
                answer="Sem limite diário disponível.",
                evidence_ids=[],
                uncertainty="alta",
                limitations=[],
            )
        item = items["budget_daily_allowance"]
        assert item.value.amount_cents == expected
        assert item.basis == "reference"
        assert item.source.input_scope.import_batch_ids == [batch.id]
        return LLMPayload(
            answer=f"O limite diário do orçamento é {item.display_value}.",
            evidence_ids=[item.evidence_id],
            uncertainty="baixa",
            limitations=[],
        )

    monkeypatch.setattr(llm_client, "call_llm", reply)
    response = client.post(
        URL, json={"question": "Qual meu limite diário?", "account_id": str(account.id)}
    )
    assert response.status_code == 200, response.text
    if expected is None:
        assert response.json()["evidences"] == []
        assert any("Limite diário indisponível" in text for text in response.json()["limitations"])
    else:
        assert response.json()["evidences"][0]["value"]["amount_cents"] == expected
        assert expected == 0 if limit == 1000 else expected > 0


def test_http_consulta_finance_real_preserva_origem_e_valida_resposta(
    client, app, db_session, reference_rows, insert_transaction, monkeypatch
):
    from tests.db.test_ai_service import current_cutoff, reference_reply
    from valyra.ai import service

    tx = insert_transaction()
    account, user = reference_rows["account"], reference_rows["user"]
    cut = current_cutoff(account, tx)
    actual_service = service.explain_for_account

    def with_clock(session, user_id, body):
        return actual_service(session, user_id, body, clock=lambda: cut)

    monkeypatch.setattr(service, "explain_for_account", with_clock)
    app.dependency_overrides[get_current_user_id] = lambda: user.id
    llm = Mock(side_effect=reference_reply)
    monkeypatch.setattr(llm_client, "call_llm", llm)
    response = client.post(URL, json={"question": "Explique", "account_id": str(account.id)})
    assert response.status_code == 200
    sent = llm.call_args.args[0]
    assert [e.source.record_id for e in sent.context_data.evidences] == [account.id, tx.id]
    assert sent.context_data.evidences[1].source.import_batch_id == tx.import_batch_id
    body = response.json()
    assert body["evidences"][0]["source"]["record_id"] == str(account.id)
    assert body["evidences"][0]["value"]["amount_cents"] == account.balance_cents
    assert any("projeção" in text for text in body["limitations"])


@pytest.mark.parametrize("target", ["other_user", "missing_account"])
def test_http_conta_alheia_e_inexistente_retornam_mesmo_404_sem_llm(
    client, app, reference_rows, monkeypatch, target
):
    account, user = reference_rows["account"], reference_rows["user"]
    user_id = uuid4() if target == "other_user" else user.id
    account_id = account.id if target == "other_user" else uuid4()
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    llm = Mock(side_effect=AssertionError("Não chamar provedor sem conta autorizada"))
    monkeypatch.setattr(llm_client, "call_llm", llm)
    response = client.post(URL, json={"question": "Explique", "account_id": str(account_id)})
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "ACCOUNT_NOT_FOUND", "message": "Conta não encontrada", "details": {}}
    }
    llm.assert_not_called()
