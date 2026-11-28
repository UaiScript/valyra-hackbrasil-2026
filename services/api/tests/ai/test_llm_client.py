"""Contrato do cliente com os SDKs reais e HTTP simulado, sem chaves reais ou cobrança."""

import json
import traceback
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from google import genai
from pydantic import ValidationError

from tests.ai.factories import context_data, make_request, money_evidence
from valyra.ai import llm_client as llm
from valyra.ai.schemas import LLMPayload
from valyra.core.config import Settings


@pytest.fixture
def payload():
    return {
        "answer": "Ainda não há dados suficientes para explicar seu orçamento.",
        "evidence_ids": [],
        "uncertainty": "alta",
        "limitations": ["Sem projeção disponível."],
    }


@pytest.fixture
def settings(monkeypatch):
    for key in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_BASE_URL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_ATTEMPTS",
        "LLM_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(key, raising=False)
    value = Settings(
        database_url="postgresql+psycopg://127.0.0.1/unused",
        gemini_api_key="test-key",
        _env_file=None,
    )
    monkeypatch.setattr(llm, "get_settings", lambda: value)
    monkeypatch.setattr(llm, "sleep", lambda _: None)
    return value


@pytest.fixture
def sdk(monkeypatch):
    state = SimpleNamespace(requests=[], clients=[], options=[])
    real_client = genai.Client

    def install(handler):
        def capture(request):
            state.requests.append(request)
            return handler(request)

        def factory(**kwargs):
            state.options.append(kwargs)
            kwargs["http_options"].client_args = {"transport": httpx.MockTransport(capture)}
            client = real_client(**kwargs)
            state.clients.append(client)
            return client

        monkeypatch.setattr(genai, "Client", factory)
        return state

    return install


@pytest.fixture
def openai_sdk_http(monkeypatch):
    import openai as openai_sdk

    state = SimpleNamespace(requests=[], clients=[], options=[])
    real_client = openai_sdk.OpenAI

    def install(handler):
        def capture(request):
            state.requests.append(request)
            return handler(request)

        def factory(**kwargs):
            state.options.append(kwargs)
            # Sem base_url explícita é a OpenAI; o Groq informa a própria base.
            options = {"base_url": "https://openai.test/v1", **kwargs}
            client = real_client(
                **options,
                http_client=httpx.Client(transport=httpx.MockTransport(capture)),
            )
            state.clients.append(client)
            return client

        monkeypatch.setattr(openai_sdk, "OpenAI", factory)
        return state

    return install


@pytest.fixture
def openai_settings(settings):
    values = Settings(database_url="unused", openai_api_key="test-openai", _env_file=None)
    settings.openai_api_key = values.openai_api_key
    settings.gemini_api_key = values.gemini_api_key
    return settings


def openai_response(payload, *, finish="stop", refusal=None):
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(payload),
                        "refusal": refusal,
                    },
                }
            ],
        },
    )


def gemini_response(payload, *, finish="STOP"):
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps(payload)}], "role": "model"},
                    "finishReason": finish,
                }
            ]
        },
    )


def test_parse_json_e_bloco_markdown(payload):
    raw = json.dumps(payload)
    assert llm._parse_response(raw).answer == payload["answer"]
    assert llm._parse_response(f"```json\n{raw}\n```").model_dump() == payload


@pytest.mark.parametrize(
    "raw",
    ["{", "{}", "```", "```python\n{}\n```", "```json\n{}\ntexto"],
)
def test_parse_invalido_tem_excecao_unica(raw):
    with pytest.raises(llm.LLMParseError):
        llm._parse_response(raw)


def test_parse_valida_ids_e_nao_expoe_conteudo(payload):
    payload["evidence_ids"] = ["SEGREDO"]
    # Confirmar que a entrada aparece no erro original e falha pela regra do ID.
    with pytest.raises(ValidationError) as original:
        LLMPayload.model_validate(payload)
    assert [(error["loc"], error["type"]) for error in original.value.errors()] == [
        (("evidence_ids", 0), "string_pattern_mismatch")
    ]
    assert "SEGREDO" in str(original.value)
    with pytest.raises(llm.LLMParseError) as caught:
        llm._parse_response(json.dumps(payload))
    assert "SEGREDO" not in str(caught.value)
    assert caught.value.__suppress_context__
    assert "SEGREDO" not in "".join(traceback.format_exception(caught.value))


def test_sucesso_com_sdk_real_limites_e_fechamento(settings, sdk, payload):
    state = sdk(lambda _: gemini_response(payload))
    result = llm.call_llm(make_request(question="Explique meu orçamento"))
    assert result.provider == "gemini"
    assert result.model == "gemini-3.8-flash"
    assert result.answer == payload["answer"]
    assert len(state.requests) == 1
    body = json.loads(state.requests[0].content)
    config = body["generationConfig"]
    assert config["maxOutputTokens"] == 4096
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"]["additionalProperties"] is False
    # Família 3 não desliga o raciocínio; o cliente pede o menor nível comum.
    assert config["thinkingConfig"] in ({"thinkingLevel": "LOW"}, {"thinking_level": "LOW"})
    assert state.requests[0].extensions["timeout"]["read"] == 30
    assert state.options[0]["http_options"].timeout == 30000
    assert state.options[0]["http_options"].retry_options.attempts == 1
    assert state.clients[0]._api_client._httpx_client.is_closed


def test_modelo_configuravel_e_familia_2_desliga_raciocinio(settings, sdk, payload):
    settings.gemini_model = "gemini-2.5-flash"
    state = sdk(lambda _: gemini_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.model == "gemini-2.5-flash"
    assert "models/gemini-2.5-flash:" in str(state.requests[0].url)
    config = json.loads(state.requests[0].content)["generationConfig"]
    assert config["thinkingConfig"] in ({"thinkingBudget": 0}, {"thinking_budget": 0})


def test_familia_2_0_nao_envia_configuracao_de_raciocinio(settings, sdk, payload):
    settings.gemini_model = "gemini-2.0-flash"
    state = sdk(lambda _: gemini_response(payload))
    llm.call_llm(make_request(question="Explique"))
    config = json.loads(state.requests[0].content)["generationConfig"]
    assert "thinkingConfig" not in config


@pytest.mark.parametrize("status", [429, 599])
def test_transitorios_respeitam_numero_de_tentativas(settings, sdk, status, caplog):
    state = sdk(
        lambda _: httpx.Response(
            status,
            json={"error": {"code": status, "message": "SEGREDO-do-provedor", "status": "UNKNOWN"}},
        )
    )
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == settings.llm_max_attempts
    assert all(client._api_client._httpx_client.is_closed for client in state.clients)
    assert "SEGREDO-do-provedor" not in caplog.text


def test_repeticao_pode_recuperar(settings, sdk, payload):
    count = 0

    def handler(_):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(503, json={"error": {"code": 503, "message": "indisponível"}})
        return gemini_response(payload)

    state = sdk(handler)
    assert llm.call_llm(make_request(question="Explique")).provider == "gemini"
    assert len(state.requests) == 2


@pytest.mark.parametrize("error", [httpx.ReadTimeout])
def test_transporte_tem_tentativas_limitadas(settings, sdk, error):
    def handler(request):
        raise error("SEGREDO", request=request)

    state = sdk(handler)
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == settings.llm_max_attempts


@pytest.mark.parametrize("status", [401])
def test_erro_permanente_nao_repete(settings, sdk, status):
    state = sdk(
        lambda _: httpx.Response(
            status,
            json={"error": {"code": status, "message": "SEGREDO", "status": "INVALID_ARGUMENT"}},
        )
    )
    with pytest.raises(llm.LLMConfigurationError) as caught:
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    assert "SEGREDO" not in str(caught.value)


@pytest.mark.parametrize("finish", ["MAX_TOKENS"])
def test_resposta_incompleta_nao_repete(settings, sdk, payload, finish):
    state = sdk(lambda _: gemini_response(payload, finish=finish))
    with pytest.raises(llm.LLMParseError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1


@pytest.mark.parametrize("gemini_key", [""])
def test_chave_ausente_nao_abre_cliente(settings, monkeypatch, gemini_key):
    settings.gemini_api_key = Settings(
        database_url="unused", gemini_api_key=gemini_key, _env_file=None
    ).gemini_api_key
    factory = Mock(side_effect=AssertionError("Não deve chamar provedor"))
    monkeypatch.setattr(genai, "Client", factory)
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    factory.assert_not_called()


@pytest.mark.parametrize("gemini_status", [429])
def test_fallback_openai_acionado_quando_gemini_indisponivel(
    settings, sdk, openai_sdk_http, payload, gemini_status
):
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    gemini = sdk(
        lambda _: httpx.Response(
            gemini_status, json={"error": {"code": gemini_status, "message": "falha"}}
        )
    )
    openai = openai_sdk_http(lambda _: openai_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.answer == payload["answer"]
    assert len(gemini.requests) == settings.llm_max_attempts
    assert len(openai.requests) == 1
    assert openai.clients[0].is_closed()


def test_fallback_nao_acionado_sem_openai_key(settings, sdk):
    # openai_api_key vazia — fallback não deve ser tentado.
    state = sdk(lambda _: httpx.Response(503, json={"error": {"code": 503, "message": "falha"}}))
    assert not settings.openai_fallback_enabled
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == settings.llm_max_attempts


def test_parse_error_nao_aciona_fallback(settings, sdk, payload, monkeypatch):
    import openai as openai_sdk

    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    openai_factory = Mock(side_effect=AssertionError("Não deve acionar fallback em parse error"))
    monkeypatch.setattr(openai_sdk, "OpenAI", openai_factory)

    # Gemini responde com finish_reason diferente de STOP — gera LLMParseError.
    state = sdk(lambda _: gemini_response(payload, finish="SAFETY"))
    with pytest.raises(llm.LLMParseError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    openai_factory.assert_not_called()


def test_chaves_mascaradas_e_fallback_por_chave(settings):
    config = Settings(
        database_url="unused",
        gemini_api_key=" test-key ",
        openai_api_key="test-openai",
        _env_file=None,
    )
    assert config.gemini_api_key.get_secret_value() == "test-key"
    assert config.gemini_enabled
    assert config.openai_fallback_enabled
    assert "test-key" not in repr(config)
    assert "test-openai" not in repr(config)


def test_openai_schema_limites_e_fechamento(openai_settings, openai_sdk_http, payload):
    state = openai_sdk_http(lambda _: openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "openai"
    body = json.loads(state.requests[0].content)
    assert body["response_format"]["type"] == "json_schema"
    schema = body["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"] == llm._RESPONSE_SCHEMA
    assert body["max_completion_tokens"] == openai_settings.llm_max_output_tokens
    assert body["model"] == "gpt-4o-mini"
    assert state.options[0]["max_retries"] == 0
    assert state.options[0]["timeout"] == openai_settings.llm_timeout_seconds
    assert state.clients[0].is_closed()


@pytest.mark.parametrize("status", [429, 599])
def test_openai_http_transitorio_limitado(openai_settings, openai_sdk_http, status, caplog):
    state = openai_sdk_http(
        lambda _: httpx.Response(
            status, json={"error": {"message": "SEGREDO-do-provedor", "code": "transient_error"}}
        )
    )
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == openai_settings.llm_max_attempts
    assert all(client.is_closed() for client in state.clients)
    assert "SEGREDO-do-provedor" not in caplog.text


@pytest.mark.parametrize(
    "code",
    ["insufficient_quota"],
)
def test_openai_limite_financeiro_nao_repete(openai_settings, openai_sdk_http, code):
    state = openai_sdk_http(
        lambda _: httpx.Response(429, json={"error": {"message": "SEGREDO", "code": code}})
    )
    with pytest.raises(llm.LLMUnavailableError, match="limite financeiro") as caught:
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    assert state.clients[0].is_closed()
    assert caught.value.__cause__ is None
    assert "SEGREDO" not in str(caught.value)


@pytest.mark.parametrize("status", [401])
def test_openai_erro_permanente_sanitizado(openai_settings, openai_sdk_http, status):
    state = openai_sdk_http(
        lambda _: httpx.Response(
            status, json={"error": {"message": "SEGREDO", "code": "invalid_request"}}
        )
    )
    with pytest.raises(llm.LLMConfigurationError) as caught:
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    assert state.clients[0].is_closed()
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert "SEGREDO" not in str(caught.value)


@pytest.mark.parametrize("error", [httpx.ReadTimeout])
def test_openai_transporte_limitado(openai_settings, openai_sdk_http, error):
    def handler(request):
        raise error("SEGREDO", request=request)

    state = openai_sdk_http(handler)
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == openai_settings.llm_max_attempts
    assert all(client.is_closed() for client in state.clients)


@pytest.mark.parametrize(
    "finish, refusal",
    [("length", None), ("stop", "Recusado")],
)
def test_openai_incompleto_ou_recusado_nao_repete(
    openai_settings, openai_sdk_http, payload, finish, refusal
):
    # Mesmo JSON completo não autoriza aceitar uma geração truncada/recusada pelo provedor.
    state = openai_sdk_http(lambda _: openai_response(payload, finish=finish, refusal=refusal))
    with pytest.raises(llm.LLMParseError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    assert state.clients[0].is_closed()


def test_gemini_erro_configuracao_nao_aciona_openai(settings, sdk, monkeypatch):
    import openai as openai_sdk

    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    state = sdk(lambda _: httpx.Response(403, json={"error": {"code": 403, "message": "falha"}}))
    factory = Mock(side_effect=AssertionError("Não deve acionar fallback"))
    monkeypatch.setattr(openai_sdk, "OpenAI", factory)
    with pytest.raises(llm.LLMConfigurationError):
        llm.call_llm(make_request(question="Explique"))
    assert len(state.requests) == 1
    factory.assert_not_called()


def test_prompt_tipado_grande_falha_antes_da_rede(settings, monkeypatch):
    data = context_data(
        evidences=[
            money_evidence(evidence_id=f"e{i}", value={"kind": "text", "value_text": "á" * 2000})
            for i in range(30)
        ]
    )
    request = make_request(context_data=data)
    factory = Mock(side_effect=AssertionError("Não deve chamar provedor"))
    monkeypatch.setattr(genai, "Client", factory)
    with pytest.raises(ValueError, match="64000"):
        llm.call_llm(request)
    factory.assert_not_called()


def _groq_key(settings):
    settings.groq_api_key = Settings(
        database_url="unused", groq_api_key="test-groq", _env_file=None
    ).groq_api_key


def _gemini_error(status):
    return lambda _: httpx.Response(status, json={"error": {"code": status, "message": "falha"}})


def _hosts(state):
    return [request.url.host for request in state.requests]


@pytest.mark.parametrize("gemini_status", [429, 503])
def test_groq_reserva_quando_gemini_indisponivel(
    settings, sdk, openai_sdk_http, payload, gemini_status
):
    _groq_key(settings)
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    gemini = sdk(_gemini_error(gemini_status))
    state = openai_sdk_http(lambda _: openai_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.provider == "groq"
    assert result.model == "openai/gpt-oss-120b"
    assert len(gemini.requests) == settings.llm_max_attempts
    # OpenAI paga não é chamada quando a reserva gratuita atende.
    assert _hosts(state) == ["api.groq.com"]
    assert state.requests[0].url.path == "/openai/v1/chat/completions"
    assert state.requests[0].headers["authorization"] == "Bearer test-groq"
    body = json.loads(state.requests[0].content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["response_format"]["json_schema"]["strict"] is False
    assert body["response_format"]["json_schema"]["schema"] == llm._RESPONSE_SCHEMA
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == settings.llm_max_output_tokens
    assert state.options[0]["max_retries"] == 0
    assert state.clients[0].is_closed()


@pytest.mark.parametrize("gemini_status", [400, 403])
def test_groq_reserva_quando_gemini_recusa_chave(
    settings, sdk, openai_sdk_http, payload, gemini_status
):
    _groq_key(settings)
    gemini = sdk(_gemini_error(gemini_status))
    state = openai_sdk_http(lambda _: openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "groq"
    assert len(gemini.requests) == 1
    assert _hosts(state) == ["api.groq.com"]


def test_groq_sem_gemini_atende_direto(settings, monkeypatch, openai_sdk_http, payload):
    settings.gemini_api_key = Settings(
        database_url="unused", gemini_api_key="", _env_file=None
    ).gemini_api_key
    _groq_key(settings)
    monkeypatch.setattr(genai, "Client", Mock(side_effect=AssertionError("Sem chave Gemini")))
    state = openai_sdk_http(lambda _: openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "groq"
    assert _hosts(state) == ["api.groq.com"]


def test_groq_modelo_configuravel_sem_raciocinio(settings, sdk, openai_sdk_http, payload):
    _groq_key(settings)
    settings.groq_model = "llama-3.3-70b-versatile"
    sdk(_gemini_error(429))
    state = openai_sdk_http(lambda _: openai_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.model == "llama-3.3-70b-versatile"
    body = json.loads(state.requests[0].content)
    assert body["model"] == "llama-3.3-70b-versatile"
    assert "reasoning_effort" not in body


@pytest.mark.parametrize("groq_status", [429, 413])
def test_openai_depois_do_groq_indisponivel(settings, sdk, openai_sdk_http, payload, groq_status):
    _groq_key(settings)
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    sdk(_gemini_error(429))

    def handler(request):
        if request.url.host == "api.groq.com":
            return httpx.Response(
                groq_status, json={"error": {"message": "SEGREDO", "code": "rate_limit_exceeded"}}
            )
        return openai_response(payload)

    state = openai_sdk_http(handler)
    result = llm.call_llm(make_request(question="Explique"))
    assert result.provider == "openai"
    # 413 (prompt acima do limite por minuto) não repete; 429 segue o teto de tentativas.
    groq_calls = 1 if groq_status == 413 else settings.llm_max_attempts
    assert _hosts(state) == ["api.groq.com"] * groq_calls + ["openai.test"]
    assert all(client.is_closed() for client in state.clients)


def test_todos_indisponiveis_gera_indisponivel(settings, sdk, openai_sdk_http):
    _groq_key(settings)
    sdk(_gemini_error(503))
    state = openai_sdk_http(
        lambda _: httpx.Response(503, json={"error": {"message": "falha", "code": "x"}})
    )
    with pytest.raises(llm.LLMUnavailableError):
        llm.call_llm(make_request(question="Explique"))
    assert _hosts(state) == ["api.groq.com"] * settings.llm_max_attempts


def test_configuracao_gemini_prevalece_se_groq_indisponivel(settings, sdk, openai_sdk_http):
    _groq_key(settings)
    sdk(_gemini_error(403))
    openai_sdk_http(lambda _: httpx.Response(503, json={"error": {"message": "x", "code": "x"}}))
    with pytest.raises(llm.LLMConfigurationError, match="Gemini"):
        llm.call_llm(make_request(question="Explique"))


def test_parse_error_nao_aciona_groq(settings, sdk, monkeypatch, payload):
    import openai as openai_sdk

    _groq_key(settings)
    factory = Mock(side_effect=AssertionError("Não deve acionar reserva em parse error"))
    monkeypatch.setattr(openai_sdk, "OpenAI", factory)
    sdk(lambda _: gemini_response(payload, finish="MAX_TOKENS"))
    with pytest.raises(llm.LLMParseError):
        llm.call_llm(make_request(question="Explique"))
    factory.assert_not_called()


def test_chave_groq_mascarada_e_aparada():
    config = Settings(database_url="unused", groq_api_key=" test-groq ", _env_file=None)
    assert config.groq_api_key.get_secret_value() == "test-groq"
    assert config.groq_fallback_enabled
    assert "test-groq" not in repr(config)
    assert not Settings(database_url="unused", _env_file=None).groq_fallback_enabled


def test_chave_groq_invalida_nao_bloqueia_openai(settings, sdk, openai_sdk_http, payload):
    _groq_key(settings)
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    sdk(_gemini_error(429))

    def handler(request):
        if request.url.host == "api.groq.com":
            return httpx.Response(401, json={"error": {"message": "x", "code": "invalid_api_key"}})
        return openai_response(payload)

    state = openai_sdk_http(handler)
    assert llm.call_llm(make_request(question="Explique")).provider == "openai"
    assert _hosts(state) == ["api.groq.com", "openai.test"]


def test_resposta_invalida_do_groq_passa_a_openai(settings, sdk, openai_sdk_http, payload):
    _groq_key(settings)
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key
    sdk(_gemini_error(429))

    def handler(request):
        if request.url.host == "api.groq.com":
            return openai_response(payload, finish="length")
        return openai_response(payload)

    state = openai_sdk_http(handler)
    assert llm.call_llm(make_request(question="Explique")).provider == "openai"
    assert _hosts(state) == ["api.groq.com", "openai.test"]


def test_resposta_invalida_do_groq_sem_openai(settings, sdk, openai_sdk_http, payload):
    _groq_key(settings)
    sdk(_gemini_error(429))
    openai_sdk_http(lambda _: openai_response(payload, finish="length"))
    with pytest.raises(llm.LLMParseError):
        llm.call_llm(make_request(question="Explique"))


def _openrouter_key(settings):
    settings.openrouter_api_key = Settings(
        database_url="unused", openrouter_api_key="test-openrouter", _env_file=None
    ).openrouter_api_key


def _openai_key(settings):
    settings.openai_api_key = Settings(
        database_url="unused", openai_api_key="test-openai", _env_file=None
    ).openai_api_key


def _fail_on(host, status, code="rate_limit_exceeded"):
    def handler(request):
        if request.url.host == host:
            return httpx.Response(status, json={"error": {"message": "SEGREDO", "code": code}})
        return None

    return handler


def test_openrouter_depois_do_groq_indisponivel(settings, sdk, openai_sdk_http, payload):
    _groq_key(settings)
    _openrouter_key(settings)
    _openai_key(settings)
    sdk(_gemini_error(429))
    groq_fails = _fail_on("api.groq.com", 429)
    state = openai_sdk_http(lambda request: groq_fails(request) or openai_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.provider == "openrouter"
    assert result.model == "openrouter/free"
    # OpenAI paga não é chamada quando a reserva de emergência gratuita atende.
    assert _hosts(state) == ["api.groq.com"] * settings.llm_max_attempts + ["openrouter.ai"]
    request = state.requests[-1]
    assert request.url.path == "/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer test-openrouter"
    body = json.loads(request.content)
    assert body["model"] == "openrouter/free"
    assert body["provider"] == {"require_parameters": True}
    assert body["response_format"]["json_schema"]["strict"] is False
    assert body["response_format"]["json_schema"]["schema"] == llm._RESPONSE_SCHEMA
    assert "reasoning_effort" not in body
    assert all(client.is_closed() for client in state.clients)


def test_openrouter_sem_groq_atende_depois_do_gemini(settings, sdk, openai_sdk_http, payload):
    _openrouter_key(settings)
    sdk(_gemini_error(503))
    state = openai_sdk_http(lambda _: openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "openrouter"
    assert _hosts(state) == ["openrouter.ai"]


@pytest.mark.parametrize("status", [402, 429])
def test_openai_depois_do_openrouter_indisponivel(settings, sdk, openai_sdk_http, payload, status):
    _openrouter_key(settings)
    _openai_key(settings)
    sdk(_gemini_error(429))
    fails = _fail_on("openrouter.ai", status)
    state = openai_sdk_http(lambda request: fails(request) or openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "openai"
    # 402 (sem saldo) não repete; 429 segue o teto de tentativas.
    calls = 1 if status == 402 else settings.llm_max_attempts
    assert _hosts(state) == ["openrouter.ai"] * calls + ["openai.test"]


def test_gemini_recusa_chave_aciona_openrouter_gratuito(settings, sdk, openai_sdk_http, payload):
    _openrouter_key(settings)
    _openai_key(settings)
    sdk(_gemini_error(403))
    state = openai_sdk_http(lambda _: openai_response(payload))
    assert llm.call_llm(make_request(question="Explique")).provider == "openrouter"
    assert _hosts(state) == ["openrouter.ai"]


def test_openrouter_modelo_pago_nao_recebe_erro_de_configuracao(
    settings, sdk, openai_sdk_http, payload
):
    _openrouter_key(settings)
    settings.openrouter_model = "anthropic/modelo-pago"
    sdk(_gemini_error(403))
    state = openai_sdk_http(lambda _: openai_response(payload))
    with pytest.raises(llm.LLMConfigurationError, match="Gemini"):
        llm.call_llm(make_request(question="Explique"))
    assert _hosts(state) == []


def test_openrouter_modelo_gratuito_configuravel(settings, sdk, openai_sdk_http, payload):
    _openrouter_key(settings)
    settings.openrouter_model = "google/gemma-4-26b-a4b-it:free"
    sdk(_gemini_error(403))
    state = openai_sdk_http(lambda _: openai_response(payload))
    result = llm.call_llm(make_request(question="Explique"))
    assert result.model == "google/gemma-4-26b-a4b-it:free"
    assert json.loads(state.requests[0].content)["model"] == "google/gemma-4-26b-a4b-it:free"


def test_resposta_invalida_do_openrouter_passa_a_openai(settings, sdk, openai_sdk_http, payload):
    _openrouter_key(settings)
    _openai_key(settings)
    sdk(_gemini_error(429))

    def handler(request):
        if request.url.host == "openrouter.ai":
            return openai_response(payload, finish="length")
        return openai_response(payload)

    state = openai_sdk_http(handler)
    assert llm.call_llm(make_request(question="Explique")).provider == "openai"
    assert _hosts(state) == ["openrouter.ai", "openai.test"]


def test_chave_openrouter_mascarada_e_aparada():
    config = Settings(database_url="unused", openrouter_api_key=" test-or ", _env_file=None)
    assert config.openrouter_api_key.get_secret_value() == "test-or"
    assert config.openrouter_fallback_enabled
    assert config.openrouter_model_is_free
    assert "test-or" not in repr(config)
    assert not Settings(database_url="unused", _env_file=None).openrouter_fallback_enabled
