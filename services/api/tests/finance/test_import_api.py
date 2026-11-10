"""Importação de CSV via HTTP (Issue #14), com banco PostgreSQL dedicado de testes."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from valyra.core.db import User
from valyra.core.deps import get_current_user_id
from valyra.finance.models import Account, ImportBatch, ImportRejection, Transaction
from valyra.seed import DEMO_ACCOUNT_ID, run

RAIZ_REPO = Path(__file__).resolve().parents[4]
CAB = b"date,description,amount\n"
URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}/import-batches"


@pytest.fixture
def seed(db_session):
    run(db_session)
    db_session.commit()


def enviar(client, conteudo: bytes, nome="extrato.csv", url=URL):
    return client.post(url, files={"file": (nome, conteudo, "text/csv")})


def test_importacao_valida(client, seed):
    r = enviar(
        client, CAB + b"2026-11-03,Supermercado BH,-89.90\n2026-11-05,Salario ACME,6000.00\n"
    )
    assert r.status_code == 201
    b = r.json()
    contadores = (b["rows_total"], b["rows_imported"], b["rows_duplicated"], b["rows_rejected"])
    assert (b["status"], *contadores) == ("completed", 2, 2, 0, 0)
    assert b["rejections"] == [] and "alerts_created" not in b


def test_reimportar_mesmo_arquivo_nao_duplica(client, seed):
    arq = CAB + b"2026-11-03,Cafe,-5.00\n"
    enviar(client, arq)
    b = enviar(client, arq).json()
    assert (b["rows_imported"], b["rows_duplicated"]) == (0, 1)


def test_duas_identicas_no_mesmo_dia_sao_importadas(client, seed):
    b = enviar(client, CAB + b"2026-11-03,Cafe,-5.00\n2026-11-03,Cafe,-5.00\n").json()
    assert b["rows_imported"] == 2


def test_linhas_invalidas_viram_rejeicoes(client, seed):
    b = enviar(client, CAB + b"2026-11-03,Ok,-1.00\n03/11/2026,Ruim,-1.00\n").json()
    assert b["rows_rejected"] == 1
    assert b["rejections"][0] == {
        "line_number": 3,
        "reason": "invalid_date",
        "raw_line": "03/11/2026,Ruim,-1.00",
    }


def test_csv_sem_colunas_retorna_422(client, seed):
    r = enviar(client, b"data,valor\n")
    assert r.status_code == 422 and r.json()["error"]["code"] == "CSV_MISSING_COLUMNS"


def test_csv_com_encoding_invalido_retorna_422(client, seed):
    r = enviar(client, CAB + "2026-11-03,Café,-1.00\n".encode("latin-1"))
    assert r.status_code == 422 and r.json()["error"]["code"] == "CSV_ENCODING"


def test_erro_de_arquivo_nao_cria_lote(client, seed, db_session):
    enviar(client, b"data,valor\n")
    assert db_session.scalar(select(func.count()).select_from(ImportBatch)) == 0


def test_arquivo_acima_de_1mb_retorna_413(client, seed):
    r = enviar(client, b"x" * (1_048_576 + 1))
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_arquivo_com_exatamente_1mb_nao_e_barrado_pelo_tamanho(client, seed):
    linha = b"2026-11-03,X,-1.00\n"
    preenchimento = b"\n" * (1_048_576 - len(CAB) - len(linha))
    r = enviar(client, CAB + linha + preenchimento)
    assert r.status_code == 201 and r.json()["rows_imported"] == 1


def test_conta_inexistente_retorna_404(client, seed):
    r = enviar(client, CAB, "a.csv", url=f"/api/v1/finance/accounts/{uuid4()}/import-batches")
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_conta_de_outro_usuario_retorna_404(client, seed, db_session):
    outro = User(name="Outra pessoa")
    db_session.add(outro)
    db_session.flush()
    conta = Account(
        user_id=outro.id, name="Alheia", balance_cents=0, balance_as_of=date(2026, 11, 1)
    )
    db_session.add(conta)
    db_session.commit()
    r = enviar(
        client,
        CAB + b"2026-11-03,X,-1.00\n",
        url=f"/api/v1/finance/accounts/{conta.id}/import-batches",
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0


def test_categoria_prevista_e_igual_a_atual_na_importacao(client, seed, db_session):
    enviar(client, CAB + b"2026-11-03,Netflix.com,-55.90\n")
    t = db_session.scalars(select(Transaction)).one()
    assert t.category_id == t.predicted_category_id
    assert t.category_source == "rule" and t.category_confidence is None
    assert t.is_recurring is False and t.anomaly_score is None
    assert t.description == "Netflix.com" and t.amount_cents == -5590


def test_lote_persistido_como_concluido(client, seed, db_session):
    b = enviar(client, CAB + b"2026-11-03,A,-1.00\n03/11/2026,Ruim,-1.00\n", "meu.csv").json()
    lote = db_session.get(ImportBatch, b["id"])
    assert (lote.status, lote.file_name, lote.account_id) == (
        "completed",
        "meu.csv",
        DEMO_ACCOUNT_ID,
    )
    assert lote.completed_at is not None
    assert db_session.scalar(select(func.count()).select_from(ImportRejection)) == 1


def test_consulta_de_lote_traz_rejeicoes(client, seed):
    lote = enviar(client, CAB + b"03/11/2026,Ruim,-1.00\n").json()
    r = client.get(f"/api/v1/finance/import-batches/{lote['id']}")
    assert r.status_code == 200 and len(r.json()["rejections"]) == 1


def test_consulta_de_lote_inexistente_retorna_404(client, seed):
    r = client.get(f"/api/v1/finance/import-batches/{uuid4()}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "IMPORT_BATCH_NOT_FOUND"


def test_lista_de_lotes_paginada(client, seed):
    enviar(client, CAB + b"2026-11-03,A,-1.00\n")
    body = client.get("/api/v1/finance/import-batches?limit=1").json()
    assert body["total"] == 1 and body["limit"] == 1 and "rejections" not in body["items"][0]


def test_lista_de_lotes_mais_recente_primeiro(client, seed):
    primeiro = enviar(client, CAB + b"2026-11-03,A,-1.00\n").json()["id"]
    segundo = enviar(client, CAB + b"2026-11-04,B,-1.00\n").json()["id"]
    ids = [item["id"] for item in client.get("/api/v1/finance/import-batches").json()["items"]]
    assert ids == [segundo, primeiro]


def test_importa_csv_de_demonstracao(client, seed):
    conteudo = (RAIZ_REPO / "datasets/samples/transactions_demo.csv").read_bytes()
    b = enviar(client, conteudo, "transactions_demo.csv").json()
    assert b["rows_rejected"] == 0 and b["rows_imported"] == b["rows_total"]


def test_falha_tecnica_desfaz_lote_e_rejeicoes(client, db_session):
    # Sem as categorias do seed a categorização falha no meio; nada da tentativa pode ficar.
    demo = User(id=get_current_user_id(), name="Usuário demo")
    db_session.add(demo)
    db_session.flush()
    db_session.add(
        Account(
            id=DEMO_ACCOUNT_ID,
            user_id=demo.id,
            name="Conta principal",
            balance_cents=0,
            balance_as_of=date(2026, 11, 1),
        )
    )
    db_session.commit()
    with pytest.raises(KeyError):
        enviar(client, CAB + b"2026-11-03,A,-1.00\n03/11/2026,Ruim,-1.00\n")
    assert db_session.scalar(select(func.count()).select_from(ImportBatch)) == 0
    assert db_session.scalar(select(func.count()).select_from(ImportRejection)) == 0


def test_arquivo_no_limite_de_5000_registros_e_importado(client, seed):
    linhas = b"".join(f"2026-11-03,Compra {i},-1.00\n".encode() for i in range(5000))
    b = enviar(client, CAB + linhas).json()
    assert (b["rows_total"], b["rows_imported"]) == (5000, 5000)
