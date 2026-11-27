"""Regras puras do relatório semanal de notícias (proposta da ADR-0013).

Lê feeds de fontes públicas, limpa o texto e liga cada notícia a temas do orçamento por
palavras-chave versionadas. Nada aqui lê banco, rede ou relógio; instantes chegam como
parâmetro. A ligação tema → categoria é um "pode afetar", nunca causa ou previsão: o LLM só
explica o que esta regra já decidiu.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Literal, Protocol
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
THEME_RULE = "news_theme_v2"
WEEK = timedelta(days=7)
# Teto do corpo do feed: um RSS de economia tem dezenas de KB; acima disso algo está errado.
MAX_FEED_BYTES = 2_000_000
# Trecho curto: a Valyra mostra título, trecho e link, nunca a matéria inteira.
EXCERPT_CHARS = 240
# Título é texto de terceiros que chega ao LLM como evidência: comprimento limitado.
TITLE_CHARS = 200

FeedFormat = Literal["rss", "ibge_json"]


@dataclass(frozen=True)
class NewsSource:
    slug: str
    name: str
    feed_url: str
    site_url: str
    license: str
    format: FeedFormat
    # Domínios de onde a imagem da notícia pode vir: só a própria fonte, nunca terceiros
    # (pixel de rastreio, conteúdo de agência parceira com reprodução proibida).
    image_hosts: tuple[str, ...] = ()


NEWS_SOURCES: tuple[NewsSource, ...] = (
    NewsSource(
        slug="agencia-brasil",
        name="Agência Brasil (EBC) — Economia",
        feed_url="https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
        site_url="https://agenciabrasil.ebc.com.br/economia",
        license="Reprodução permitida com citação da Agência Brasil; aqui só título, trecho e link",
        format="rss",
        image_hosts=("ebc.com.br",),
    ),
    NewsSource(
        slug="bcb-notas",
        name="Banco Central do Brasil — Notas à imprensa",
        feed_url="https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/notasImprensa",
        site_url="https://www.bcb.gov.br/detalhenoticia",
        license="Conteúdo público do Banco Central; citar a fonte",
        format="rss",
        image_hosts=("bcb.gov.br",),
    ),
    NewsSource(
        slug="ibge-noticias",
        name="Agência de Notícias do IBGE",
        feed_url="https://servicodados.ibge.gov.br/api/v3/noticias/",
        site_url="https://agenciadenoticias.ibge.gov.br/",
        license="Conteúdo público do IBGE; citar a fonte",
        format="ibge_json",
        image_hosts=("ibge.gov.br",),
    ),
)
SOURCES_BY_SLUG = {source.slug: source for source in NEWS_SOURCES}


class FeedFormatError(ValueError):
    """Feed fora do formato esperado; a coleta registra e segue para a próxima fonte."""


@dataclass(frozen=True)
class FeedItem:
    source_slug: str
    title: str
    excerpt: str
    link: str
    # Instante informado pela fonte; None quando o feed não traz data confiável.
    source_published_at: datetime | None
    # Imagem publicada pela própria fonte junto da notícia, e o crédito quando o feed traz.
    image_url: str | None = None
    image_credit: str | None = None


def news_key(source_slug: str, link: str) -> str:
    """Chave estável da notícia: a mesma matéria coletada duas vezes vira a mesma chave."""
    return f"news:{source_slug}:{sha256(link.encode('utf-8')).hexdigest()[:16]}"


_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def clean_text(raw: str | None) -> str:
    """Texto sem HTML nem entidades, em uma linha."""
    if not raw:
        return ""
    text = html.unescape(_TAGS.sub(" ", html.unescape(raw)))
    return _SPACES.sub(" ", text).strip()


def excerpt(raw: str | None, limit: int = EXCERPT_CHARS) -> str:
    text = clean_text(raw)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return f"{cut}…"


def _http_link(raw: str | None) -> str | None:
    link = clean_text(raw)
    return link if re.fullmatch(r"https?://\S+", link) else None


def _aware(moment: datetime) -> datetime:
    # Data sem fuso é horário de Brasília: as três fontes publicam no horário oficial.
    return moment.replace(tzinfo=BUSINESS_ZONE) if moment.tzinfo is None else moment


def _rss_date(raw: str | None) -> datetime | None:
    text = clean_text(raw)
    if not text:
        return None
    try:
        return _aware(parsedate_to_datetime(text)).astimezone(UTC)
    except (TypeError, ValueError):
        pass
    try:
        return _aware(datetime.fromisoformat(text.replace("Z", "+00:00"))).astimezone(UTC)
    except ValueError:
        return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, *names: str) -> str | None:
    for child in element:
        if _local_name(child.tag) in names and child.text:
            return child.text
    return None


_IMG_SRC = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)
_IMAGE_EXT = re.compile(r"\.(?:jpe?g|png|webp|gif)(?:$|\?)", re.IGNORECASE)


def safe_image_url(source_slug: str, raw: str | None, base: str | None = None) -> str | None:
    """URL https de imagem hospedada na própria fonte; qualquer outra coisa vira None."""
    text = clean_text(raw)
    if not text:
        return None
    url = urljoin(base, text) if base else text
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    source = SOURCES_BY_SLUG.get(source_slug)
    if parts.scheme != "https" or source is None or not host:
        return None
    if not any(host == allowed or host.endswith(f".{allowed}") for allowed in source.image_hosts):
        return None
    return url if len(url) <= 1000 else None


def _rss_image(node: ET.Element) -> tuple[str | None, str | None]:
    """Imagem do item: media:content/thumbnail, enclosure de imagem ou primeiro <img>."""
    credit = None
    for child in node.iter():
        if _local_name(child.tag) == "credit" and child.text:
            credit = clean_text(child.text) or None
    for child in node.iter():
        name = _local_name(child.tag)
        url = child.get("url")
        if not url:
            continue
        kind = (child.get("type") or child.get("medium") or "").lower()
        if name in {"content", "thumbnail"} and (
            "image" in kind or not kind and _IMAGE_EXT.search(url)
        ):
            return url, credit
        if name == "enclosure" and kind.startswith("image"):
            return url, credit
    html_text = _child_text(node, "encoded", "description") or ""
    match = _IMG_SRC.search(html.unescape(html_text))
    return (match.group(1) if match else None), credit


def parse_rss(source_slug: str, body: bytes) -> list[FeedItem]:
    """Itens de um RSS 2.0. DOCTYPE e entidades são recusados antes do parser (XXE, bombas)."""
    if len(body) > MAX_FEED_BYTES:
        raise FeedFormatError("feed acima do tamanho máximo")
    head = body[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in body.lower():
        raise FeedFormatError("feed com DOCTYPE ou entidades não é aceito")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise FeedFormatError("XML inválido") from None
    if _local_name(root.tag) != "rss":
        raise FeedFormatError("raiz do feed não é <rss>")
    items: list[FeedItem] = []
    for node in root.iter():
        if _local_name(node.tag) != "item":
            continue
        title = excerpt(_child_text(node, "title"), TITLE_CHARS)
        link = _http_link(_child_text(node, "link", "guid"))
        if not title or link is None:
            continue
        raw_image, credit = _rss_image(node)
        image_url = safe_image_url(source_slug, raw_image, link)
        items.append(
            FeedItem(
                source_slug=source_slug,
                title=title,
                excerpt=excerpt(_child_text(node, "description", "encoded")),
                link=link,
                source_published_at=_rss_date(_child_text(node, "pubDate", "date")),
                image_url=image_url,
                image_credit=credit[:200] if credit and image_url else None,
            )
        )
    return items


_IBGE_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})(?: (\d{2}):(\d{2})(?::(\d{2}))?)?$")


def _ibge_date(raw: object) -> datetime | None:
    match = _IBGE_DATE.fullmatch(clean_text(str(raw or "")))
    if match is None:
        return _rss_date(str(raw or ""))
    day, month, year, hour, minute, second = match.groups()
    try:
        moment = datetime(
            int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0)
        )
    except ValueError:
        return None
    return moment.replace(tzinfo=BUSINESS_ZONE).astimezone(UTC)


IBGE_IMAGE_BASE = "https://agenciadenoticias.ibge.gov.br/"


def _ibge_image(raw: object) -> str | None:
    """`imagens` chega como texto JSON (`{"image_intro": "images/..."}`), com caminho relativo."""
    data: object = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(data, dict):
        return None
    for key in ("image_intro", "image_fulltext"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_ibge(source_slug: str, payload: object) -> list[FeedItem]:
    """Itens da API de notícias do IBGE: `{"items": [{"titulo", "introducao", ...}]}`."""
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise FeedFormatError("resposta do IBGE sem lista de itens")
    items: list[FeedItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = excerpt(str(row.get("titulo") or ""), TITLE_CHARS)
        link = _http_link(str(row.get("link") or ""))
        if not title or link is None:
            continue
        items.append(
            FeedItem(
                source_slug=source_slug,
                title=title,
                excerpt=excerpt(str(row.get("introducao") or "")),
                link=link,
                source_published_at=_ibge_date(row.get("data_publicacao")),
                image_url=safe_image_url(
                    source_slug, _ibge_image(row.get("imagens")), IBGE_IMAGE_BASE
                ),
            )
        )
    return items


def publication_instant(item: FeedItem, ingested_at: datetime) -> datetime:
    """Publicação gravada: a da fonte, nunca depois da coleta; sem data, a própria coleta.

    Data futura no feed (fuso errado, agendamento) não pode fazer a notícia "aparecer" antes
    de a Valyra tê-la visto, então o teto é o instante da coleta.
    """
    if item.source_published_at is None:
        return ingested_at
    return min(item.source_published_at, ingested_at)


# ---------- Temas do orçamento (regra news_theme_v2) ----------
# Ordem importa: temas específicos vêm antes dos genéricos (juros, inflação), porque a
# notícia entra no primeiro tema que casar e "preço" aparece em quase toda matéria.


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    # Frase fixa de "por que olhar": diz o que pode mudar, sem número nem previsão.
    why: str
    keywords: tuple[str, ...]
    category_slugs: tuple[str, ...]
    # Tema do radar Alpha com os dados observados que dão contexto à manchete.
    radar_theme: str | None = None


# Ações acompanhadas no radar (brapi) e como aparecem nas manchetes. "Vale" sozinho é
# palavra comum ("vale a pena"), então só entram formas que nomeiam a empresa.
TICKER_ALIASES: dict[str, tuple[str, ...]] = {
    "PETR4": ("petrobras", "petr4"),
    "VALE3": ("vale3", "mineradora vale", "acoes da vale", "vale s.a"),
    "ITUB4": ("itau", "itau unibanco", "itub4"),
    "MGLU3": ("magazine luiza", "magalu", "mglu3"),
}


THEMES: tuple[Theme, ...] = (
    Theme(
        key="acoes",
        title="Ações que você acompanha",
        why=(
            "Ajuda a ler o movimento das ações que você acompanha; o radar mostra a "
            "variação do dia, sem prever a próxima."
        ),
        keywords=tuple(alias for aliases in TICKER_ALIASES.values() for alias in aliases),
        category_slugs=(),
        radar_theme="acoes",
    ),
    Theme(
        key="agro",
        title="Agro e cadeia da soja",
        why=(
            "Safra e clima nos polos de grãos podem chegar ao preço de óleo, carnes e "
            "derivados no mercado."
        ),
        keywords=(
            "soja",
            "milho",
            "safra",
            "agronegocio",
            "agro",
            "colheita",
            "plantio",
            "estiagem",
            "seca",
            "conab",
            "graos",
            "el nino",
            "la nina",
        ),  # fmt: skip
        category_slugs=("mercado",),
        radar_theme="clima",
    ),
    Theme(
        key="combustiveis",
        title="Combustíveis e transporte",
        why="Combustível e tarifas mudam o custo de corridas, ônibus e deslocamentos.",
        keywords=(
            "gasolina",
            "combustivel",
            "combustiveis",
            "diesel",
            "etanol",
            "petrobras",
            "passagem",
            "tarifa de onibus",
            "transporte publico",
        ),  # fmt: skip
        category_slugs=("transporte",),
    ),
    Theme(
        key="contas",
        title="Energia e contas da casa",
        why="Tarifa de energia, água e telefonia entra direto nas contas do mês.",
        keywords=(
            "energia",
            "conta de luz",
            "bandeira tarifaria",
            "aneel",
            "tarifa de agua",
            "saneamento",
            "telefonia",
        ),  # fmt: skip
        category_slugs=("contas-e-servicos",),
    ),
    Theme(
        key="alimentos",
        title="Alimentos",
        why="Alta ou queda de alimentos pesa na ida ao mercado.",
        keywords=(
            "alimento",
            "alimentos",
            "cesta basica",
            "arroz",
            "feijao",
            "cafe",
            "carne",
            "leite",
            "hortifruti",
        ),  # fmt: skip
        category_slugs=("mercado",),
        radar_theme="inflacao",
    ),
    Theme(
        key="moradia",
        title="Aluguel e moradia",
        why="Índices de reajuste e crédito imobiliário mudam o valor do aluguel e do condomínio.",
        keywords=("aluguel", "igp-m", "igpm", "financiamento imobiliario", "imovel", "imoveis"),
        category_slugs=("moradia",),
    ),
    Theme(
        key="credito",
        title="Crédito e dívidas",
        why="Regras de cartão, rotativo e empréstimos mudam o custo de dever.",
        keywords=(
            "cartao de credito",
            "rotativo",
            "endividamento",
            "inadimplencia",
            "emprestimo",
            "credito consignado",
            "desenrola",
        ),  # fmt: skip
        category_slugs=(),
    ),
    Theme(
        key="renda",
        title="Renda, emprego e impostos",
        why="Salário mínimo, imposto de renda e emprego mudam quanto entra no mês.",
        keywords=(
            "salario minimo",
            "imposto de renda",
            "desemprego",
            "emprego",
            "fgts",
            "decimo terceiro",
            "13o salario",
            "isencao",
        ),  # fmt: skip
        category_slugs=("salario",),
    ),
    Theme(
        key="juros",
        title="Juros e Selic",
        why="Mexe no rendimento da reserva atrelada ao CDI e no custo de parcelamentos e cartão.",
        keywords=("selic", "copom", "juros", "taxa basica", "cdi", "politica monetaria"),
        category_slugs=(),
        radar_theme="juros",
    ),
    Theme(
        key="inflacao",
        title="Inflação e preços",
        why="Preços em geral costumam aparecer primeiro no mercado e em restaurantes.",
        keywords=("ipca", "inflacao", "inpc", "custo de vida", "preco", "precos", "deflacao"),
        category_slugs=("mercado", "restaurantes"),
        radar_theme="inflacao",
    ),
)
THEMES_BY_KEY = {theme.key: theme for theme in THEMES}


def tickers_for(title: str, excerpt_text: str) -> tuple[str, ...]:
    """Tickers do radar citados pelo nome da empresa na manchete ou no trecho."""
    text = normalize(f"{title} {excerpt_text}")
    return tuple(
        ticker
        for ticker, aliases in TICKER_ALIASES.items()
        if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text) for alias in aliases)
    )


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def themes_for(title: str, excerpt_text: str) -> tuple[str, ...]:
    """Temas cujas palavras aparecem inteiras no título ou no trecho, na ordem de THEMES."""
    text = normalize(f"{title} {excerpt_text}")
    found: list[str] = []
    for theme in THEMES:
        if any(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) for word in theme.keywords):
            found.append(theme.key)
    return tuple(found)


class NewsRow(Protocol):
    signal_key: str
    title: str
    summary: str
    published_at: datetime


@dataclass(frozen=True)
class ThemeGroup[R]:
    theme: Theme
    items: list[R]


@dataclass(frozen=True)
class WeeklyDigest[R]:
    week_start: datetime
    week_end: datetime
    groups: list[ThemeGroup[R]]
    total: int
    unmatched: int


def week_start(as_of: datetime) -> datetime:
    return as_of - WEEK


def build_digest[R: NewsRow](
    rows: Iterable[R], as_of: datetime, *, per_theme: int = 4
) -> WeeklyDigest[R]:
    """Agrupa as notícias da semana até o corte por tema; nada publicado depois entra.

    Uma notícia pode tocar mais de um tema, mas aparece só no primeiro de THEMES (o mais
    específico), para o relatório não repetir manchete.
    """
    start = week_start(as_of)
    seen: set[str] = set()
    week: list[R] = []
    for row in sorted(rows, key=lambda r: r.published_at, reverse=True):
        if row.signal_key in seen or not start <= row.published_at <= as_of:
            continue
        seen.add(row.signal_key)
        week.append(row)
    buckets: dict[str, list[R]] = {}
    unmatched = 0
    for row in week:
        keys = themes_for(row.title, row.summary)
        if not keys:
            unmatched += 1
            continue
        buckets.setdefault(keys[0], []).append(row)
    order = {theme.key: index for index, theme in enumerate(THEMES)}
    groups = [
        ThemeGroup(theme=THEMES_BY_KEY[key], items=items[:per_theme])
        for key, items in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), order[kv[0]]))
    ]
    return WeeklyDigest(
        week_start=start, week_end=as_of, groups=groups, total=len(week), unmatched=unmatched
    )
