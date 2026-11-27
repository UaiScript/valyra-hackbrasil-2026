"""Orçamento mensal por categoria de saída."""

from datetime import date

import pytest

from valyra.core import clock

URL = "/api/v1/finance/budgets"


def categoria(client, slug: str) -> str:
    itens = client.get("/api/v1/finance/categories").json()["items"]
    return next(c["id"] for c in itens if c["slug"] == slug)


@pytest.fixture(autouse=True)
def hoje(monkeypatch):
    # Fixa "hoje" sem depender do relógio nem do DEMO_TODAY do ambiente.
    monkeypatch.setattr(clock, "get_today", lambda: date(2026, 11, 7))


@pytest.fixture
def gastos(client, seed, importar):
    # A linha de 20/11 é posterior a "hoje" e não entra no consumo realizado.
    importar(
        b"2026-11-02,Supermercado Bom Dia,-300.00\n"
        b"2026-11-03,Hortifruti Central,-150.00\n"
        b"2026-11-04,Ifood pedido,-90.00\n"
        b"2026-11-05,Salario,5000.00\n"
        b"2026-11-20,Supermercado Bom Dia,-999.00\n"
    )


def test_sem_limites_devolve_lista_vazia(client, seed):
    r = client.get(URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"] == []
    assert body["total_limit_cents"] == 0
    assert body["total_spent_cents"] == 0


def test_define_limite_e_calcula_consumo_e_status(client, gastos):
    mercado = categoria(client, "mercado")
    restaurantes = categoria(client, "restaurantes")

    r = client.put(f"{URL}/{mercado}", json={"limit_cents": 40000})
    assert r.status_code == 200, r.text
    client.put(f"{URL}/{restaurantes}", json={"limit_cents": 10000})

    body = client.get(URL, params={"month": "2026-11"}).json()
    por_slug = {item["category"]["slug"]: item for item in body["items"]}
    assert por_slug["mercado"] == {
        **por_slug["mercado"],
        "limit_cents": 40000,
        "spent_cents": 45000,
        "remaining_cents": -5000,
        "status": "over",
    }
    assert por_slug["restaurantes"]["spent_cents"] == 9000
    assert por_slug["restaurantes"]["status"] == "warning"
    assert body["total_limit_cents"] == 50000
    assert body["total_spent_cents"] == 54000


def test_put_troca_limite_existente(client, gastos):
    mercado = categoria(client, "mercado")
    client.put(f"{URL}/{mercado}", json={"limit_cents": 40000})
    body = client.put(f"{URL}/{mercado}", json={"limit_cents": 100000}).json()
    assert [(i["limit_cents"], i["status"]) for i in body["items"]] == [(100000, "ok")]


def test_mes_sem_gastos_tem_consumo_zero(client, gastos):
    client.put(f"{URL}/{categoria(client, 'mercado')}", json={"limit_cents": 40000})
    body = client.get(URL, params={"month": "2026-10"}).json()
    assert body["items"][0]["spent_cents"] == 0
    assert body["items"][0]["status"] == "ok"


def test_categoria_de_entrada_e_recusada(client, seed):
    r = client.put(f"{URL}/{categoria(client, 'salario')}", json={"limit_cents": 1000})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CATEGORY_KIND_MISMATCH"


def test_categoria_inexistente(client, seed):
    r = client.put(f"{URL}/00000000-0000-0000-0000-00000000dead", json={"limit_cents": 1000})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


@pytest.mark.parametrize(
    "corpo",
    [
        {"limit_cents": 0},
        {"limit_cents": -5},
        {"limit_cents": 1.5},
        {"limit_cents": "100"},
        {},
        {"limit_cents": 10, "extra": 1},
    ],
)
def test_corpo_invalido(client, seed, corpo):
    r = client.put(f"{URL}/{categoria(client, 'mercado')}", json=corpo)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_remove_limite(client, seed):
    mercado = categoria(client, "mercado")
    client.put(f"{URL}/{mercado}", json={"limit_cents": 40000})
    assert client.delete(f"{URL}/{mercado}").status_code == 204
    assert client.get(URL).json()["items"] == []
    r = client.delete(f"{URL}/{mercado}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "BUDGET_NOT_FOUND"
