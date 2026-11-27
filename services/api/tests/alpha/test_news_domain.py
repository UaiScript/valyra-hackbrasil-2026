"""Regras puras do relatório semanal de notícias: leitura de feeds, temas e janela."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from valyra.alpha.news import (
    EXCERPT_CHARS,
    FeedFormatError,
    FeedItem,
    build_digest,
    clean_text,
    excerpt,
    news_key,
    parse_ibge,
    parse_rss,
    publication_instant,
    safe_image_url,
    themes_for,
    tickers_for,
)

FIXTURE = Path(__file__).parent / "fixtures" / "news_rss.xml"


def test_rss_le_titulo_trecho_link_e_data_com_fuso():
    items = parse_rss("agencia-brasil", FIXTURE.read_bytes())
    assert [item.title for item in items][:2] == [
        "Copom mantém a taxa Selic na reunião desta semana",
        "Gasolina fica mais cara nos postos, diz levantamento",
    ]
    assert len(items) == 3  # item sem link fica fora
    first = items[0]
    assert first.excerpt == "Comitê de Política Monetária & o comunicado da reunião."
    assert first.source_published_at == datetime(2026, 11, 26, 0, 30, tzinfo=UTC)
    assert first.link.startswith("https://agenciabrasil.ebc.com.br/")
    assert first.image_url == "https://imagens.ebc.com.br/teste/copom.jpg"
    assert first.image_credit == "Fotógrafo/Agência Brasil"
    # Imagem de outro domínio (pixel de rastreio) não entra.
    assert items[1].image_url is None and items[1].image_credit is None


@pytest.mark.parametrize(
    "body",
    [
        b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "x">]><rss><channel/></rss>',
        b"<rss><channel><item>",
        b"<feed xmlns='http://www.w3.org/2005/Atom'/>",
    ],
)
def test_rss_recusa_doctype_xml_quebrado_e_outra_raiz(body):
    with pytest.raises(FeedFormatError):
        parse_rss("x", body)


def test_link_que_nao_e_http_fica_fora():
    body = (
        b"<rss><channel><item><title>Selic</title><link>javascript:alert(1)</link>"
        b"</item></channel></rss>"
    )
    assert parse_rss("x", body) == []


def test_ibge_le_data_brasileira_como_horario_de_brasilia():
    payload = {
        "items": [
            {
                "titulo": "IPCA de outubro fica abaixo do mês anterior",
                "introducao": "<b>Inflação</b> oficial do mês.",
                "link": "https://agenciadenoticias.ibge.gov.br/teste-ipca",
                "data_publicacao": "10/11/2026 09:00:00",
                "imagens": '{"image_intro":"images/agenciadenoticias/teste/ipca.jpg"}',
            },
            {"titulo": "Sem link", "link": ""},
        ]
    }
    [item] = parse_ibge("ibge-noticias", payload)
    assert item.source_published_at == datetime(2026, 11, 10, 12, tzinfo=UTC)
    assert item.excerpt == "Inflação oficial do mês."
    assert item.image_url == (
        "https://agenciadenoticias.ibge.gov.br/images/agenciadenoticias/teste/ipca.jpg"
    )
    with pytest.raises(FeedFormatError):
        parse_ibge("ibge-noticias", ["x"])


def test_trecho_curto_e_texto_limpo():
    assert clean_text("  a&nbsp;<br/>b  ") == "a b"
    long = "palavra " * 100
    cut = excerpt(long)
    assert len(cut) <= EXCERPT_CHARS + 1 and cut.endswith("…")


def test_publicacao_nunca_depois_da_coleta():
    collected = datetime(2026, 11, 27, 12, tzinfo=UTC)
    future = FeedItem("x", "t", "", "https://a.test/1", collected + timedelta(hours=3))
    past = FeedItem("x", "t", "", "https://a.test/2", collected - timedelta(days=1))
    missing = FeedItem("x", "t", "", "https://a.test/3", None)
    assert publication_instant(future, collected) == collected
    assert publication_instant(past, collected) == collected - timedelta(days=1)
    assert publication_instant(missing, collected) == collected


def test_chave_estavel_por_fonte_e_link():
    assert news_key("a", "https://x.test/1") == news_key("a", "https://x.test/1")
    assert news_key("a", "https://x.test/1") != news_key("b", "https://x.test/1")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Copom mantém a Selic", ("juros",)),
        ("Conta de luz terá bandeira tarifária amarela", ("contas",)),
        ("Preço do café e da carne sobe no atacado", ("alimentos", "inflacao")),
        ("Petrobras reduz o diesel", ("acoes", "combustiveis")),
        ("Salário mínimo de 2027 é anunciado", ("renda",)),
        ("Colheita de soja avança em Mato Grosso", ("agro",)),
        ("Estiagem preocupa produtores de milho", ("agro",)),
        ("Mineradora Vale paga dividendos", ("acoes",)),
        ("Feira de tecnologia reúne startups", ()),
        # Palavra inteira: "cafeteria" não é "café", "internet" não casa com "inter".
        ("Nova cafeteria abre no centro", ()),
    ],
)
def test_temas_por_palavra_inteira_sem_acento(title, expected):
    assert themes_for(title, "") == expected


@dataclass
class Row:
    signal_key: str
    title: str
    summary: str
    published_at: datetime


def test_relatorio_da_semana_respeita_corte_e_agrupa_por_tema():
    as_of = datetime(2026, 11, 27, 12, tzinfo=UTC)
    rows = [
        Row("k1", "Copom mantém a Selic", "", as_of - timedelta(days=1)),
        Row("k2", "Juros do cartão de crédito sobem", "", as_of - timedelta(days=2)),
        Row("k3", "Gasolina sobe", "", as_of - timedelta(days=3)),
        Row("k4", "Feira de tecnologia", "", as_of - timedelta(days=1)),
        # Publicada depois do corte: não pode aparecer (data leakage).
        Row("k5", "Selic muda amanhã", "", as_of + timedelta(minutes=1)),
        # Fora da janela de 7 dias.
        Row("k6", "Selic antiga", "", as_of - timedelta(days=8)),
        Row("k1", "Copom mantém a Selic", "", as_of - timedelta(days=1)),
    ]
    digest = build_digest(rows, as_of)
    assert digest.total == 4 and digest.unmatched == 1
    # Empate em quantidade segue a ordem de THEMES; cartão é crédito antes de ser juros.
    assert [group.theme.key for group in digest.groups] == ["combustiveis", "credito", "juros"]
    assert [row.signal_key for row in digest.groups[2].items] == ["k1"]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Petrobras e Itaú lideram negociações na bolsa", ("PETR4", "ITUB4")),
        ("Mineradora Vale divulga produção do trimestre", ("VALE3",)),
        ("Magalu abre novas lojas", ("MGLU3",)),
        # "Vale" como verbo não é a empresa.
        ("Vale a pena antecipar o 13º?", ()),
    ],
)
def test_acoes_do_radar_pelo_nome_da_empresa(title, expected):
    assert tickers_for(title, "") == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://imagens.ebc.com.br/a.jpg", "https://imagens.ebc.com.br/a.jpg"),
        ("http://imagens.ebc.com.br/a.jpg", None),
        ("https://ebc.com.br.malicioso.test/a.jpg", None),
        ("javascript:alert(1)", None),
        ("", None),
    ],
)
def test_imagem_so_https_e_do_dominio_da_fonte(raw, expected):
    assert safe_image_url("agencia-brasil", raw) == expected
