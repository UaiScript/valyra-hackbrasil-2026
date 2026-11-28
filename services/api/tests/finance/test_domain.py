"""Bordas do CSV: precisão monetária, enquadramento e identidade dos registros."""

import csv
from datetime import date
from decimal import Inexact, localcontext
from uuid import UUID, uuid4

import pytest

from valyra.finance.domain import (
    MAX_FILE_BYTES,
    CsvFormatError,
    ParsedRow,
    RejectedRow,
    categorize,
    compute_row_hashes,
    parse_csv,
)

CAB = b"date,description,amount\n"


@pytest.mark.parametrize(
    "linha,motivo",
    [
        (b"03/11/2026,Mercado,-10.00", "invalid_date"),
        (b"2026-11-03,Mercado,abc", "invalid_amount"),
        (b"2026-11-03,Mercado,-89,90", "wrong_column_count"),
        (b'2026-11-03,Mercado,"-89,90"', "invalid_amount"),
        (b"2026-11-03,Mercado,0.00", "zero_amount"),
        (b"2026-11-03,   ,-10.00", "empty_description"),
    ],
)
def test_linha_rejeitada_com_motivo(linha, motivo):
    r = parse_csv(CAB + linha + b"\n")
    assert r.rows == [] and r.rejected[0].reason == motivo and r.rejected[0].line_number == 2


@pytest.mark.parametrize(
    "descricao,valor,slug",
    [
        ("Salario ACME", 600000, "salario"),
        ("Pix recebido Joao", 15000, "outras-receitas"),
        ("Loja qualquer", -4000, "outros"),
    ],
)
def test_categorize(descricao, valor, slug):
    assert categorize(descricao, valor) == slug


@pytest.mark.parametrize(
    "header",
    [
        "date,description",
        "date,description,amount,extra",
        "date,date,amount",
        "amount,description,date",
    ],
)
def test_cabecalho_na_ordem_contratada_sem_duplicatas_ou_extras(header):
    with pytest.raises(CsvFormatError) as error:
        parse_csv((header + "\n").encode())
    assert error.value.code == "CSV_MISSING_COLUMNS"


@pytest.mark.parametrize(
    "amount",
    ["NaN", "1e2", "1.001", "92233720368547758.08", "-92233720368547758.09"],
)
def test_valores_fora_do_formato_ou_bigint_sao_invalid_amount(amount):
    result = parse_csv(CAB + f"2026-11-03,X,{amount}\n".encode())
    assert result.rows == []
    assert result.rejected == [RejectedRow(2, "invalid_amount", f"2026-11-03,X,{amount}")]


@pytest.mark.parametrize("amount", ["-0.00"])
def test_zero_com_qualquer_representacao_valida_e_rejeitado(amount):
    result = parse_csv(CAB + f"2026-11-03,X,{amount}\n".encode())
    assert result.rejected[0].reason == "zero_amount"


@pytest.mark.parametrize(
    "amount,cents",
    [
        ("92233720368547758.07", 2**63 - 1),
        ("-92233720368547758.08", -(2**63)),
        ("90071992547409.93", 9007199254740993),
    ],
)
def test_conversao_exata_nos_limites_independe_do_contexto_decimal(amount, cents):
    with localcontext() as context:
        context.prec = 3
        context.traps[Inexact] = True
        result = parse_csv(CAB + f"2026-11-03,X,{amount}\n".encode())
        assert result.rows[0].amount_cents == cents
        assert type(result.rows[0].amount_cents) is int
        assert context.prec == 3


def test_preserva_descricao_original_inclusive_aspas_virgula_e_crlf_interno():
    text = (
        "date,description,amount\r\n\r\n"
        '2026-11-03,"  Compras,\r\nloja ""A""  ",-12.50\r\n'
        '2026-11-03,"linha\r\nruim",abc\r\n'
        "2026-11-04,Posto,-5.00\r\n"
    )
    result = parse_csv(text.encode())
    assert result.rows == [
        ParsedRow(3, date(2026, 11, 3), '  Compras,\r\nloja "A"  ', -1250),
        ParsedRow(7, date(2026, 11, 4), "Posto", -500),
    ]
    assert result.rejected == [
        RejectedRow(5, "invalid_amount", '2026-11-03,"linha\r\nruim",abc'),
    ]
    assert result.total == 3


def test_aspas_malformadas_sao_rejeitadas_e_proximo_registro_e_processado():
    raw = '2026-11-03,"texto"x,-1'
    result = parse_csv(CAB + (raw + "\n2026-11-04,Valida,-2\n").encode())
    assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
    assert result.rows == [ParsedRow(3, date(2026, 11, 4), "Valida", -200)]
    assert result.total == 2


def test_limite_conta_rejeicoes_mas_nao_linhas_em_branco():
    content = CAB + b"2026-11-03,X,-1\n" * 4999 + b"\n" * 25 + b"ruim,X,-1\n"
    result = parse_csv(content)
    assert result.total == 5000
    assert result.rejected[0].line_number == 5026
    with pytest.raises(CsvFormatError) as error:
        parse_csv(content + b"ruim,X,-1\n")
    assert error.value.code == "CSV_TOO_MANY_ROWS"


def test_limite_e_de_registros_csv_nao_de_linhas_fisicas():
    result = parse_csv(CAB + b'2026-11-03,"linha\ncontinua",-1\n' * 5000)
    assert result.total == 5000
    assert result.rows[-1].line_number == 10000


def test_hash_utiliza_preimagem_contratada_e_nao_numero_da_linha():
    from hashlib import sha256

    account = UUID("00000000-0000-0000-0000-000000000123")
    row = ParsedRow(99, date(2026, 11, 3), "  CAFÉ ", -500)
    expected = sha256(b"00000000-0000-0000-0000-000000000123|2026-11-03|-500|cafe|1").hexdigest()
    assert compute_row_hashes(account, [row]) == [expected]
    assert len(expected) == 64
    assert compute_row_hashes(account, [ParsedRow(2, row.date, "cafe", -500)]) == [expected]


def test_ocorrencias_contam_por_chave_normalizada_mesmo_intercaladas():
    account = uuid4()
    first = ParsedRow(2, date(2026, 11, 3), "Café", -500)
    other = ParsedRow(3, date(2026, 11, 4), "Café", -500)
    repeat = ParsedRow(4, first.date, " CAFE ", first.amount_cents)
    rows = [first, other, repeat]
    hashes = compute_row_hashes(account, rows)
    assert hashes == compute_row_hashes(account, rows)
    assert len(set(hashes)) == 3
    assert hashes[1] == compute_row_hashes(account, [other])[0]
    assert hashes[2] == compute_row_hashes(account, [first, repeat])[1]
    assert len(set(compute_row_hashes(account, [first, first]))) == 2
    assert rows == [first, other, repeat]
    assert compute_row_hashes(account, []) == []


@pytest.mark.parametrize("change", ["date", "amount", "description"])
def test_hash_muda_quando_muda_campo_da_identidade(change):
    row = ParsedRow(2, date(2026, 11, 3), "Cafe", -500)
    values = {"date": row.date, "description": row.description, "amount_cents": row.amount_cents}
    values[{"amount": "amount_cents"}.get(change, change)] = {
        "date": date(2026, 11, 4),
        "amount": 500,
        "description": "Mercado",
    }[change]
    account = uuid4()
    assert compute_row_hashes(account, [row]) != compute_row_hashes(
        account, [ParsedRow(2, **values)]
    )


@pytest.mark.parametrize(
    "text,slug",
    [
        ("HORTIFRÚTI", "mercado"),
        ("FARMÁCIA", "saude"),
        ("DISNEY+", "assinaturas"),
    ],
)
def test_regras_de_despesa_normalizam_acentos_e_respeitam_sinal(text, slug):
    assert categorize(text, -1) == slug
    assert categorize(text, 1) == "outras-receitas"


@pytest.mark.parametrize("text", ["xnetflix", "uber_trip"])
def test_palavra_inteira_nao_casa_com_substrings(text):
    assert categorize(text, -1) == "outros"


def test_precedencia_usa_ordem_das_regras_nao_posicao_na_descricao():
    assert categorize("Uber supermercado", -1) == "mercado"
    assert categorize("Netflix padaria", -1) == "restaurantes"
    assert categorize("Mercado salário", 1) == "salario"
    assert categorize("Folha ACME", 1) == "salario"
    assert categorize("Salário ACME", -1) == "outros"


@pytest.mark.parametrize("field_limit", [32])
def test_limite_de_campo_csv_reader_e_respeitado_sem_alteracao_global(field_limit):
    # Explicitly accepted restriction: the domain must not mutate this global
    # process setting. The test temporarily sets it and always restores it.
    previous = csv.field_size_limit(field_limit)
    try:
        raw = '2026-11-03,"' + "x" * (field_limit + 1) + '",-1'
        content = CAB + (raw + "\n2026-11-04,Valida,-2\n").encode()
        assert len(content) < MAX_FILE_BYTES
        result = parse_csv(content)
        assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
        assert result.rows == [ParsedRow(3, date(2026, 11, 4), "Valida", -200)]
        assert result.total == 2
        assert csv.field_size_limit() == field_limit
    finally:
        csv.field_size_limit(previous)


def test_estouro_de_campo_multilinha_nao_importa_fragmentos_da_descricao():
    previous = csv.field_size_limit(32)
    try:
        raw = '2026-11-03,"' + "x" * 33 + '\n2026-11-04,Fragmento,-99\nfecho",-1'
        result = parse_csv(CAB + (raw + "\n2026-11-05,Valida,-2\n").encode())
        assert result.rows == [ParsedRow(5, date(2026, 11, 5), "Valida", -200)]
        assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
        assert result.total == 2
        assert csv.field_size_limit() == 32
    finally:
        csv.field_size_limit(previous)


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_multilinha_malformada_preserva_todo_texto_e_recupera_no_registro_seguinte(ending):
    raw = ending.join(['2026-11-03,"inicio', "2026-11-04,Fragmento,-99", 'fecho"x,-1'])
    result = parse_csv(
        (
            "date,description,amount" + ending + raw + ending + "2026-11-05,Valida,-2" + ending
        ).encode()
    )
    assert result.rows == [ParsedRow(5, date(2026, 11, 5), "Valida", -200)]
    assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
    assert result.total == 2
