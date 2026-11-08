"""Acceptance examples from Issue #13, followed by domain edge cases."""

import ast
import csv
import sys
from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Inexact, localcontext
from io import StringIO
from itertools import product
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from valyra.finance.domain import (
    CATEGORY_RULES,
    MAX_FILE_BYTES,
    MAX_ROWS,
    CsvFormatError,
    ParsedRow,
    ParseResult,
    RejectedRow,
    categorize,
    compute_row_hashes,
    normalize_description,
    parse_csv,
)

CAB = b"date,description,amount\n"


def test_linha_valida():
    r = parse_csv(CAB + b"2026-11-03,Supermercado BH,-89.90\n")
    assert r.rows == [ParsedRow(2, date(2026, 11, 3), "Supermercado BH", -8990)]
    assert r.rejected == [] and r.total == 1


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


def test_aceita_bom_utf8():
    assert len(parse_csv(b"\xef\xbb\xbf" + CAB + b"2026-11-03,X,-1.00\n").rows) == 1


def test_aceita_crlf():
    assert len(parse_csv(b"date,description,amount\r\n2026-11-03,X,-1.00\r\n").rows) == 1


def test_aceita_cabecalho_com_espacos_e_maiusculas():
    assert len(parse_csv(b" Date ,Description,AMOUNT\n2026-11-03,X,-1.00\n").rows) == 1


@pytest.mark.parametrize(
    "texto,centavos", [("-89.90", -8990), ("1500", 150000), ("0.5", 50), ("-0.01", -1)]
)
def test_converte_reais_para_centavos(texto, centavos):
    linha = f"2026-11-03,X,{texto}\n".encode()
    assert parse_csv(CAB + linha).rows[0].amount_cents == centavos


def test_mais_de_duas_casas_decimais_e_rejeitado():
    assert parse_csv(CAB + b"2026-11-03,X,-1.234\n").rejected[0].reason == "invalid_amount"


def test_ignora_linhas_vazias_no_fim():
    r = parse_csv(CAB + b"2026-11-03,X,-1.00\n\n\n")
    assert r.total == 1 and r.rejected == []


def test_apenas_cabecalho_resulta_em_zero_linhas():
    r = parse_csv(CAB)
    assert r.rows == [] and r.rejected == [] and r.total == 0


def test_colunas_ausentes_gera_erro_de_arquivo():
    with pytest.raises(CsvFormatError) as e:
        parse_csv(b"data,valor\n")
    assert e.value.code == "CSV_MISSING_COLUMNS"


def test_encoding_invalido_gera_erro_de_arquivo():
    with pytest.raises(CsvFormatError) as e:
        parse_csv(CAB + "2026-11-03,Café,-1.00\n".encode("latin-1"))
    assert e.value.code == "CSV_ENCODING"


def test_mais_de_5000_linhas_gera_erro_de_arquivo():
    corpo = b"".join(b"2026-11-03,X,-1.00\n" for _ in range(5001))
    with pytest.raises(CsvFormatError) as e:
        parse_csv(CAB + corpo)
    assert e.value.code == "CSV_TOO_MANY_ROWS"


def test_normalize_description():
    assert normalize_description("  Café  da  MANHÃ ") == "cafe da manha"


def test_hashes_iguais_para_mesmo_arquivo():
    rows = parse_csv(CAB + b"2026-11-03,Cafe,-5.00\n").rows
    conta = uuid4()
    assert compute_row_hashes(conta, rows) == compute_row_hashes(conta, rows)


def test_transacoes_identicas_no_mesmo_dia_tem_hashes_diferentes():
    rows = parse_csv(CAB + b"2026-11-03,Cafe,-5.00\n2026-11-03,Cafe,-5.00\n").rows
    h = compute_row_hashes(uuid4(), rows)
    assert len(set(h)) == 2


def test_hash_muda_entre_contas():
    rows = parse_csv(CAB + b"2026-11-03,Cafe,-5.00\n").rows
    assert compute_row_hashes(uuid4(), rows) != compute_row_hashes(uuid4(), rows)


@pytest.mark.parametrize(
    "descricao,valor,slug",
    [
        ("SUPERMERCADO BH", -12000, "mercado"),
        ("Uber *Trip", -2350, "transporte"),
        ("Netflix.com", -5590, "assinaturas"),
        ("Aluguel novembro", -180000, "moradia"),
        ("Salario ACME", 600000, "salario"),
        ("Pix recebido Joao", 15000, "outras-receitas"),
        ("Loja qualquer", -4000, "outros"),
    ],
)
def test_categorize(descricao, valor, slug):
    assert categorize(descricao, valor) == slug


def test_limites_publicos():
    assert MAX_FILE_BYTES == 1_048_576
    assert MAX_ROWS == 5000


@pytest.mark.parametrize(
    "instance,names",
    [
        (
            ParsedRow(2, date(2026, 11, 3), "Original", -1),
            ["line_number", "date", "description", "amount_cents"],
        ),
        (RejectedRow(2, "invalid_date", "original"), ["line_number", "reason", "raw_line"]),
        (ParseResult([], [], 0), ["rows", "rejected", "total"]),
    ],
)
def test_dataclasses_conservam_interface_e_sao_frozen(instance, names):
    assert [field.name for field in fields(instance)] == names
    with pytest.raises(FrozenInstanceError):
        setattr(instance, names[0], None)


@pytest.mark.parametrize("content", [b"", b"\xef\xbb\xbf", b"\n", b"\n" + CAB])
def test_arquivo_sem_cabecalho_na_primeira_linha(content):
    with pytest.raises(CsvFormatError) as error:
        parse_csv(content)
    assert error.value.code == "CSV_MISSING_COLUMNS"


@pytest.mark.parametrize(
    "header",
    [
        "date,description",
        "date,description,amount,extra",
        "date,date,amount",
        "date,description,description",
        "amount,description,date",
        "date,description,amount,AMOUNT",
        '"date"x,description,amount',
        '"date,description,amount',
        "date;description;amount",
    ],
)
def test_cabecalho_na_ordem_contratada_sem_duplicatas_ou_extras(header):
    with pytest.raises(CsvFormatError) as error:
        parse_csv((header + "\n").encode())
    assert error.value.code == "CSV_MISSING_COLUMNS"


@pytest.mark.parametrize(
    "text",
    [
        "20261103",
        "2026-1-03",
        "2026-11-3",
        "2026-W45-2",
        "2026-307",
        "2026-11-03T00:00:00",
        "2026-11-03Z",
        " 2026-11-03",
        "2026-11-03 ",
        "2025-02-29",
        "2026-04-31",
        "0000-01-01",
        "2026-00-01",
        "2026-01-00",
    ],
)
def test_data_tem_formato_estrito_e_validade_de_calendario(text):
    result = parse_csv(CAB + f"{text},X,-1\n".encode())
    assert result.rejected == [RejectedRow(2, "invalid_date", f"{text},X,-1")]


@pytest.mark.parametrize("text", ["0001-01-01", "2024-02-29", "9999-12-31"])
def test_datas_validas_incluem_ano_bissexto_e_limites(text):
    assert parse_csv(CAB + f"{text},X,1\n".encode()).rows[0].date == date.fromisoformat(text)


@pytest.mark.parametrize(
    "amount",
    [
        "",
        "+1",
        "1.",
        ".5",
        "-.5",
        "1e2",
        "NaN",
        "Infinity",
        "-Infinity",
        "1_000",
        "R$ 1",
        " 1.00",
        "1.00 ",
        "1.001",
        "0.001",
        "--1",
        "92233720368547758.08",
        "-92233720368547758.09",
        "9" * 1000,
    ],
)
def test_valores_fora_do_formato_ou_bigint_sao_invalid_amount(amount):
    result = parse_csv(CAB + f"2026-11-03,X,{amount}\n".encode())
    assert result.rows == []
    assert result.rejected == [RejectedRow(2, "invalid_amount", f"2026-11-03,X,{amount}")]


@pytest.mark.parametrize("amount", ["0", "0.0", "0.00", "-0", "-0.00", "000.00"])
def test_zero_com_qualquer_representacao_valida_e_rejeitado(amount):
    result = parse_csv(CAB + f"2026-11-03,X,{amount}\n".encode())
    assert result.rejected[0].reason == "zero_amount"


@pytest.mark.parametrize(
    "amount,cents",
    [
        ("92233720368547758.07", 2**63 - 1),
        ("-92233720368547758.08", -(2**63)),
        ("90071992547409.93", 9007199254740993),
        ("0001.20", 120),
        ("0" * 1000 + "1.01", 101),
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


def test_aceita_todos_os_campos_entre_aspas():
    result = parse_csv(CAB + b'"2026-11-03","Mercado, bairro","-1.00"\n')
    assert result.rows == [ParsedRow(2, date(2026, 11, 3), "Mercado, bairro", -100)]


def test_ignora_apenas_linhas_fisicas_em_branco_e_preserva_numeracao():
    result = parse_csv(CAB + b'\n \t\r\n2026-11-03,X,-1\n\n,,\n""\n')
    assert [row.line_number for row in result.rows] == [4]
    assert result.rejected == [
        RejectedRow(6, "invalid_date", ",,"),
        RejectedRow(7, "wrong_column_count", '""'),
    ]
    assert result.total == 3


@pytest.mark.parametrize("ending", ["", "\n", "\r\n", "\r"])
def test_raw_line_preserva_texto_e_remove_so_terminador_do_registro(ending):
    raw = '2026-11-03,"texto, original",abc'
    result = parse_csv(CAB + (raw + ending).encode())
    assert result.rejected == [RejectedRow(2, "invalid_amount", raw)]


def test_aspas_malformadas_sao_rejeitadas_e_proximo_registro_e_processado():
    raw = '2026-11-03,"texto"x,-1'
    result = parse_csv(CAB + (raw + "\n2026-11-04,Valida,-2\n").encode())
    assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
    assert result.rows == [ParsedRow(3, date(2026, 11, 4), "Valida", -200)]
    assert result.total == 2


def test_registro_truncado_rejeita_todo_trecho_consumido_ate_eof():
    raw = '2026-11-03,"texto\ncontinua\n2026-11-04,X,-2'
    result = parse_csv(CAB + (raw + "\n").encode())
    assert result.rows == []
    assert result.rejected == [RejectedRow(2, "wrong_column_count", raw)]
    assert result.total == 1


def test_precedencia_de_rejeicoes_segue_colunas_data_descricao_valor():
    result = parse_csv(CAB + b"ruim,,abc,extra\nruim,,abc\n2026-11-03,,abc\n")
    assert [r.reason for r in result.rejected] == [
        "wrong_column_count",
        "invalid_date",
        "empty_description",
    ]


@pytest.mark.parametrize("row", [b"2026-11-03,X,-1\n", b"ruim,X,-1\n"])
def test_aceita_exatamente_5000_registros_validos_ou_rejeitados(row):
    result = parse_csv(CAB + row * 5000)
    assert result.total == len(result.rows) + len(result.rejected) == 5000


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


def test_tamanho_em_bytes_e_responsabilidade_do_router():
    record = b'2026-11-03,"' + b"x" * 100_000 + b'",-1\n'
    content = CAB + record * 11
    assert len(content) > MAX_FILE_BYTES
    assert parse_csv(content).total == 11


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Café\tDA\nMANHÃ", "cafe da manha"),
        ("Cafe\u0301", "cafe"),
        ("\u00a0  ÁGUA\u2003 e pão  ", "agua e pao"),
        ("PIX *Uber-99", "pix *uber-99"),
        ("", ""),
        (" ", ""),
        ("A|B", "a|b"),
    ],
)
def test_normalizacao_e_idempotente_sem_remover_pontuacao(text, expected):
    assert normalize_description(text) == expected
    assert normalize_description(normalize_description(text)) == expected


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
        ("PADARIA", "restaurantes"),
        ("99 *TRIP", "transporte"),
        ("CONDOMÍNIO", "moradia"),
        ("COPASA", "contas-e-servicos"),
        ("FARMÁCIA", "saude"),
        ("LIVRARIA", "educacao"),
        ("INGRESSO", "lazer"),
        ("DISNEY+", "assinaturas"),
    ],
)
def test_regras_de_despesa_normalizam_acentos_e_respeitam_sinal(text, slug):
    assert categorize(text, -1) == slug
    assert categorize(text, 1) == "outras-receitas"


@pytest.mark.parametrize(
    "text", ["1999", "Uberlandia", "primeiro", "supermercados", "xnetflix", "uber_trip"]
)
def test_palavra_inteira_nao_casa_com_substrings(text):
    assert categorize(text, -1) == "outros"


def test_precedencia_usa_ordem_das_regras_nao_posicao_na_descricao():
    assert categorize("Uber supermercado", -1) == "mercado"
    assert categorize("Netflix padaria", -1) == "restaurantes"
    assert categorize("Mercado salário", 1) == "salario"
    assert categorize("Folha ACME", 1) == "salario"
    assert categorize("Salário ACME", -1) == "outros"


def test_regras_tem_interface_e_ordem_registradas():
    assert isinstance(CATEGORY_RULES, list)
    assert [slug for slug, _ in CATEGORY_RULES] == [
        "mercado",
        "restaurantes",
        "transporte",
        "moradia",
        "contas-e-servicos",
        "saude",
        "educacao",
        "lazer",
        "assinaturas",
        "salario",
    ]
    assert all(isinstance(words, tuple) for _, words in CATEGORY_RULES)


def test_categorize_rejeita_zero_que_nao_e_transacao_valida():
    with pytest.raises(ValueError):
        categorize("X", 0)


def test_dominio_importa_apenas_biblioteca_padrao_sem_banco_http_ou_ia():
    import valyra.finance.domain as domain

    tree = ast.parse(Path(domain.__file__).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            names.add(node.module.split(".")[0])
    assert names <= sys.stdlib_module_names | {"__future__"}
    assert not names & {"sqlite3", "http", "urllib", "socket"}


@pytest.mark.parametrize("field_limit", [32, 131_072])
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


@pytest.mark.parametrize("separator", ["\u2028", "\u0085", "\v", "\f"])
def test_separadores_unicode_nao_sao_confundidos_com_linhas_fisicas_csv(separator):
    raw = f'2026-11-03,"A{separator}B",abc'
    result = parse_csv(CAB + (raw + "\n2026-11-04,X,-1\n").encode())
    assert result.rejected == [RejectedRow(2, "invalid_amount", raw)]
    assert result.rows[0].line_number == 3


@pytest.mark.parametrize(
    "slug,keywords",
    [
        ("mercado", ("supermercado", "mercado", "atacadao", "hortifruti")),
        ("restaurantes", ("restaurante", "ifood", "lanchonete", "padaria")),
        ("transporte", ("uber", "99", "combustivel", "posto", "estacionamento")),
        ("moradia", ("aluguel", "condominio")),
        ("contas-e-servicos", ("energia", "cemig", "agua", "copasa", "internet", "telefone")),
        ("saude", ("farmacia", "drogaria", "hospital", "clinica")),
        ("educacao", ("escola", "faculdade", "curso", "livraria")),
        ("lazer", ("cinema", "show", "ingresso")),
        ("assinaturas", ("netflix", "spotify", "prime", "disney")),
        ("salario", ("salario", "folha")),
    ],
)
def test_todas_as_palavras_chave_minimas_da_issue(slug, keywords):
    amount = 1 if slug == "salario" else -1
    for keyword in keywords:
        assert categorize(f"PIX {keyword.upper()} / DEMO", amount) == slug


def test_linha_somente_com_espacos_nao_conta_mesmo_se_excede_limite_de_campo():
    result = parse_csv(CAB + b" " * 150_000 + b"\n2026-11-03,X,-1\n")
    assert result.rows == [ParsedRow(3, date(2026, 11, 3), "X", -100)]
    assert result.rejected == []
    assert result.total == 1


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


@pytest.mark.parametrize("field_limit,accepted", [(131_072, False), (200_000, True)])
def test_mesmo_arquivo_respeita_limite_efetivo_do_ambiente(field_limit, accepted):
    previous = csv.field_size_limit(field_limit)
    try:
        raw = '2026-11-03,"' + "x" * 150_000 + '",-1'
        result = parse_csv(CAB + (raw + "\n").encode())
        assert result.total == 1
        assert bool(result.rows) is accepted
        assert bool(result.rejected) is not accepted
        assert csv.field_size_limit() == field_limit
    finally:
        csv.field_size_limit(previous)


@pytest.mark.parametrize(
    "ending,quoting",
    [
        ("\r\n", csv.QUOTE_MINIMAL),
        ("\n", csv.QUOTE_ALL),
        ("\r\n", csv.QUOTE_ALL),
        ("\r", csv.QUOTE_ALL),
    ],
)
def test_enquadramento_equivale_ao_csv_reader_com_aspas_e_quebras_combinadas(ending, quoting):
    descriptions = [
        "X" + a + b
        for a, b in product(["texto", ",", '"', "\n", "\r", "\r\n", "\u2028", " "], repeat=2)
    ]
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator=ending, quoting=quoting)
    writer.writerow(["date", "description", "amount"])
    writer.writerows(["2026-11-03", text, "-1"] for text in descriptions)
    content = stream.getvalue()
    reference = csv.reader(StringIO(content, newline=""), strict=True)
    next(reference)
    expected = []
    while True:
        first_line = reference.line_num + 1
        try:
            _, description, _ = next(reference)
        except StopIteration:
            break
        expected.append(ParsedRow(first_line, date(2026, 11, 3), description, -100))
    result = parse_csv(content.encode())
    assert result.rows == expected
    assert result.rejected == []
    assert result.total == len(descriptions)


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
