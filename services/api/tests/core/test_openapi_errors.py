"""Contrato de erros (#41): o OpenAPI declara o envelope real, não o 422 padrão do FastAPI."""

import json

ERROR_REF = "#/components/schemas/ErrorResponse"

# Códigos 4xx por operação, levantados dos AppError dos routers/services Finance e Alerts.
EXPECTED_4XX = {
    "finance_create_import_batch": {"404", "413", "422"},
    "finance_list_import_batches": {"422"},
    "finance_get_import_batch": {"404", "422"},
    "finance_list_accounts": {"422"},
    "finance_update_account": {"404", "422"},
    "finance_list_transactions": {"404", "422"},
    "finance_update_transaction": {"404", "422"},
    "finance_list_categories": {"422"},
    "finance_get_summary": {"404", "422"},
    "finance_get_projection": {"404", "422"},
    "finance_get_budgets": {"422"},
    "finance_set_budget": {"404", "422"},
    "finance_delete_budget": {"404", "422"},
    "alerts_list": {"422"},
    "alerts_update": {"404", "422"},
    "alpha_get_forecasts": {"422"},
    "alpha_get_radar": {"422"},
    "alpha_get_weekly_news": {"422"},
}


def _operations(spec):
    for methods in spec["paths"].values():
        for operation in methods.values():
            yield operation["operationId"], operation


def test_validacao_padrao_do_fastapi_nao_aparece(app):
    spec = app.openapi()
    assert "HTTPValidationError" not in spec["components"]["schemas"]
    assert "ValidationError" not in spec["components"]["schemas"]
    assert "HTTPValidationError" not in json.dumps(spec)


def test_error_response_descreve_envelope(app):
    schemas = app.openapi()["components"]["schemas"]
    assert schemas["ErrorResponse"]["required"] == ["error"]
    body = schemas["ErrorBody"]
    assert set(body["required"]) == {"code", "message", "details"}
    assert body["properties"]["details"]["type"] == "object"


def test_cada_operacao_finance_alerts_e_alpha_declara_seus_4xx_com_envelope(app):
    finance = {
        op_id: operation
        for op_id, operation in _operations(app.openapi())
        if op_id.startswith(("finance_", "alerts_", "alpha_"))
    }
    # Rota nova sem entrada na tabela quebra o teste até declarar seus erros.
    assert set(finance) == set(EXPECTED_4XX)
    for op_id, operation in finance.items():
        declared = {status for status in operation["responses"] if status.startswith("4")}
        assert declared == EXPECTED_4XX[op_id], op_id
        for status in declared:
            schema = operation["responses"][status]["content"]["application/json"]["schema"]
            assert schema == {"$ref": ERROR_REF}, (op_id, status)
