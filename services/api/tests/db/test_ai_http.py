"""Jornada HTTP com conta/transação sintéticas no Finance real e LLM simulado."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from valyra.ai import llm_client
from valyra.core.deps import get_current_user_id

pytestmark = pytest.mark.postgres
URL = "/api/v1/ai/explain"


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
