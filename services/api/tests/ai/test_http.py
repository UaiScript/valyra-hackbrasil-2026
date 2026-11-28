"""Jornada HTTP IA com contexto sintético e transporte/cliente simulados, sem banco."""

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from google import genai
from pydantic import ValidationError
from sqlalchemy.orm import Session

from tests.ai.factories import ACCOUNT_ID, crowded_context
from valyra.ai import llm_client, service
from valyra.ai.domain import EvidenceContextError, EvidenceReferenceError, UnsupportedClaimError
from valyra.ai.llm_client import (
    LLMConfigurationError,
    LLMParseError,
    LLMPromptError,
    LLMUnavailableError,
)
from valyra.ai.schemas import EvidenceContext, LLMPayload, LLMResponse
from valyra.alpha.news_service import WeeklyReport
from valyra.alpha.service import Radar
from valyra.core.config import Settings
from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.errors import AppError

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

URL = "/api/v1/ai/explain"
BODY = {"question": "Explique meu saldo de referência", "account_id": ACCOUNT_ID}
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
# Captura antes das substituições de cada teste, sem criar cliente de rede.
_REAL_CALL_LLM = llm_client.call_llm


@pytest.fixture
def stack(app, monkeypatch):
    session = Mock(spec=Session)
    account = SimpleNamespace(
        id=UUID(ACCOUNT_ID),
        balance_cents=500000,
        balance_as_of=date(2020, 11, 1),
        updated_at=datetime(2020, 11, 1, tzinfo=UTC),
    )
    authorize = Mock(return_value=account)
    transactions = Mock(return_value=([], 0))
    llm = Mock(side_effect=AssertionError("Teste deve instalar seu cliente simulado"))
    monkeypatch.setattr(service.finance_service, "get_account_for_user", authorize)
    monkeypatch.setattr(service.finance_service, "list_transactions", transactions)
    # Sem lote concluído: o contexto não traz cálculos Finance nestes testes HTTP.
    monkeypatch.setattr(
        service.finance_service, "list_completed_import_batches", Mock(return_value=[])
    )
    monkeypatch.setattr(service.finance_service, "is_anomalous", Mock(return_value=False))
    # Radar vazio: sem coletas Alpha, o contexto declara a ausência como limitação.
    monkeypatch.setattr(service.alpha_service, "get_radar", Mock(return_value=EMPTY_RADAR))
    # Sem notícias coletadas: o relatório semanal não acrescenta evidências.
    monkeypatch.setattr(service.news_service, "get_weekly_report", Mock(return_value=EMPTY_NEWS))
    monkeypatch.setattr(llm_client, "call_llm", llm)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    with TestClient(app) as client:
        yield SimpleNamespace(
            http=client,
            account=account,
            authorize=authorize,
            transactions=transactions,
            llm=llm,
            session=session,
        )


def valid_reply(sent):
    evidence = sent.context_data.evidences[0]
    return LLMResponse(
        answer=f"O saldo de referência informado é {evidence.display_value}.",
        evidence_ids=[evidence.evidence_id],
        uncertainty="alta",
        limitations=["Não é uma projeção."],
        provider="gemini",
        model="modelo-interno",
    )


def test_http_monta_contexto_autoriza_valida_e_serializa_apenas_contrato_publico(stack):
    stack.llm.side_effect = valid_reply
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 200
    body = response.json()
    sent = stack.llm.call_args.args[0]
    assert sent.question == BODY["question"]
    assert body["as_of"] == sent.context_data.model_dump(mode="json")["as_of"]
    assert set(body) == {"answer", "as_of", "evidences", "uncertainty", "limitations"}
    assert "R$ 5.000,00" in body["answer"]
    assert body["evidences"][0]["value"]["amount_cents"] == 500000
    assert body["evidences"][0]["source"]["record_id"] == ACCOUNT_ID
    assert "display_value" not in body["evidences"][0]
    assert any("Alpha" in item for item in body["limitations"])
    stack.authorize.assert_called_with(stack.session, USER_ID, UUID(ACCOUNT_ID))
    stack.session.commit.assert_not_called()
    stack.session.rollback.assert_not_called()


@pytest.mark.parametrize("large_context", [False, True])
def test_jornada_http_inclui_prompt_sdk_parsing_e_dominio_sem_chamada_paga(
    stack, monkeypatch, large_context
):
    # Restaura o cliente real: somente o transporte HTTP do SDK é substituído.
    real_client = genai.Client
    captured = []
    settings = Settings(
        database_url="unused",
        gemini_api_key="fake-test-key",
        openai_api_key="",
        llm_max_attempts=1,
        _env_file=None,
    )
    monkeypatch.setattr(llm_client, "get_settings", lambda: settings)
    original = None
    if large_context:

        def provider(_session, _uid, _account, cut, _clock):
            nonlocal original
            original = EvidenceContext.model_validate(crowded_context(as_of=cut, built_at=cut))
            return original

        monkeypatch.setattr(service, "_finance_context", provider)

    def transport(request):
        wire = json.loads(request.content)
        prompt = json.loads(wire["contents"][0]["parts"][0]["text"])
        assert len(wire["contents"][0]["parts"][0]["text"].encode("utf-8")) <= 64000
        captured.append(prompt)
        evidence = prompt["context_data"]["evidences"][0]
        payload = {
            "answer": f"O saldo de referência é {evidence['display_value']}.",
            "evidence_ids": [evidence["evidence_id"]],
            "uncertainty": "alta",
            "limitations": ["Não há resumo disponível."],
        }
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": json.dumps(payload)}], "role": "model"},
                        "finishReason": "STOP",
                    }
                ]
            },
        )

    def factory(**kwargs):
        kwargs["http_options"].client_args = {"transport": httpx.MockTransport(transport)}
        return real_client(**kwargs)

    monkeypatch.setattr(genai, "Client", factory)
    monkeypatch.setattr(llm_client, "call_llm", _REAL_CALL_LLM)
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 200
    assert len(captured) == 1 and captured[0]["question"] == BODY["question"]
    assert captured[0]["context_data"]["account_id"] == ACCOUNT_ID
    assert response.json()["evidences"][0]["value"]["amount_cents"] == 500000
    if large_context:
        sent = captured[0]["context_data"]
        assert len(sent["evidences"]) < len(original.evidences)
        ids = {item["evidence_id"] for item in sent["evidences"]}
        assert {"e1", "input_tx", "e3"} <= ids
        for item in sent["evidences"]:
            assert set(item["source"].get("input_evidence_ids", [])) <= ids
        assert any("Contexto parcial" in text for text in response.json()["limitations"])
        assert any("Publicação estimada" in text for text in response.json()["limitations"])
        assert len(original.evidences) == 33


@pytest.mark.parametrize(
    "answer,ids",
    [
        ("Saldo R$ 999,00.", ["account_reference_balance"]),
        ("Saldo R$ 5.000,00.", ["fonte_inventada"]),
        ("Saldo em 2099-01-01.", ["account_reference_balance"]),
    ],
)
def test_resposta_sem_suporte_nao_e_entregue_como_sucesso(stack, answer, ids):
    stack.llm.side_effect = lambda _: LLMPayload(
        answer=answer, evidence_ids=ids, uncertainty="alta", limitations=[]
    )
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "AI_INVALID_RESPONSE"
    assert "answer" not in response.json()
    assert "999" not in response.text and "fonte_inventada" not in response.text
    assert stack.llm.call_count == 1


def test_contexto_sem_evidencias_retorna_insuficiencia_sem_provedor(stack):
    stack.account.balance_cents = 2**63 - 1
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 200
    body = response.json()
    assert body["evidences"] == [] and body["uncertainty"] == "alta"
    assert any("precisão" in text for text in body["limitations"])
    stack.llm.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"question": " "},
        {"question": "x" * 2001},
        {"question": 123},
        {"account_id": "invalida"},
        {"account_id": None},
        {"context_data": {}},
        {"user_id": str(USER_ID)},
        {"history": []},
        {"as_of": "2020-01-01T00:00:00Z"},
        {"evidence_ids": []},
        {"model": "outro"},
    ],
)
def test_corpo_invalido_nao_busca_contexto_nem_chama_llm(stack, changes):
    response = stack.http.post(URL, json=BODY | changes)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in response.json()["error"]["details"]
    stack.authorize.assert_not_called()
    stack.transactions.assert_not_called()
    stack.llm.assert_not_called()


def test_conta_indisponivel_preserva_404_sem_chamar_contexto_ou_llm(stack):
    stack.authorize.side_effect = AppError("ACCOUNT_NOT_FOUND", "Conta não encontrada", 404)
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "ACCOUNT_NOT_FOUND", "message": "Conta não encontrada", "details": {}}
    }
    stack.transactions.assert_not_called()
    stack.llm.assert_not_called()


@pytest.mark.parametrize(
    "error,status,code",
    [
        (LLMUnavailableError("SEGREDO"), 503, "AI_UNAVAILABLE"),
        (LLMConfigurationError("SEGREDO"), 500, "AI_CONFIGURATION_ERROR"),
        (LLMParseError("SEGREDO"), 502, "AI_INVALID_RESPONSE"),
        (EvidenceReferenceError("SEGREDO"), 502, "AI_INVALID_RESPONSE"),
        (UnsupportedClaimError("SEGREDO"), 502, "AI_INVALID_RESPONSE"),
        (EvidenceContextError("SEGREDO"), 500, "AI_CONTEXT_INVALID"),
        (LLMPromptError("SEGREDO"), 500, "AI_CONTEXT_INVALID"),
        (ValidationError.from_exception_data("SEGREDO", []), 500, "AI_CONTEXT_INVALID"),
    ],
)
def test_falhas_conhecidas_usam_envelope_sem_expor_dados(stack, error, status, code):
    stack.llm.side_effect = error
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == {}
    assert "SEGREDO" not in response.text and "answer" not in response.json()


def test_sem_chaves_retorna_503_depois_de_autorizar_sem_criar_sdk(stack, monkeypatch):
    monkeypatch.setattr(llm_client, "call_llm", _REAL_CALL_LLM)
    monkeypatch.setattr(
        llm_client,
        "get_settings",
        lambda: Settings(
            database_url="unused", gemini_api_key="", openai_api_key="", _env_file=None
        ),
    )
    sdk = Mock(side_effect=AssertionError("Sem chaves não abrir SDK"))
    monkeypatch.setattr(genai, "Client", sdk)
    response = stack.http.post(URL, json=BODY)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_UNAVAILABLE"
    sdk.assert_not_called()


def test_openapi_expoe_contrato_publico_e_envelope_real(app):
    spec = app.openapi()
    operation = spec["paths"][URL]["post"]
    assert operation["operationId"] == "ai_explain"
    schemas = spec["components"]["schemas"]
    assert set(schemas["ExplainRequest"]["properties"]) == {"question", "account_id"}
    assert schemas["ExplainRequest"]["additionalProperties"] is False
    assert set(schemas["ExplainResponse"]["properties"]) == {
        "answer",
        "as_of",
        "evidences",
        "uncertainty",
        "limitations",
    }
    assert "LLMRequest" not in schemas and "LLMResponse" not in schemas
    assert "display_value" not in schemas["EvidenceItem"]["properties"]
    assert {"404", "422", "500", "502", "503"} <= operation["responses"].keys()
    for status in ("404", "422", "500", "502", "503"):
        assert operation["responses"][status]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
