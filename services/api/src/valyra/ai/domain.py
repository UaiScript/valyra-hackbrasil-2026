"""Validação estrutural/lexical da ADR-0011, sem I/O ou chamadas ao LLM.

Confere citações, metadados temporais e reprodução literal de valores com unidade.
Não demonstra causalidade, veracidade externa, vínculo semântico entre cada frase
e métrica, nem identifica toda quantidade escrita por extenso ou implícita.
"""

import re
import unicodedata
from datetime import date, datetime
from typing import get_args

from pydantic import ValidationError

from valyra.ai.schemas import (
    AlphaSignalSource,
    CalculationSource,
    EvidenceContext,
    EvidenceItem,
    ExplainResponse,
    FinanceRecordSource,
    IntegerValue,
    LLMPayload,
    NonMonetaryUnit,
    TextValue,
)

# Reconhecer unidades não autorizadas também evita aceitar um valor correto com
# moeda, escala ou unidade trocada. Só as apresentações originais são permitidas.
_UNITS = (
    *get_args(NonMonetaryUnit),
    "BRL",
    "USD",
    "EUR",
    "GBP",
    "real",
    "reais",
    "euro",
    "euros",
    "dólar",
    "dólares",
    "centavo",
    "centavos",
    "dia",
    "dias",
    "ano",
    "anos",
    "mil",
    "milhão",
    "milhões",
    "bilhão",
    "bilhões",
    "k",
    "m",
)
_UNIT_PATTERN = "|".join(
    re.escape(unit.casefold()) for unit in sorted(_UNITS, key=len, reverse=True)
)
_CURRENCY = r"(?:r\$|us\$|u\$|\$|€|£|brl|usd|eur|gbp)"
_NUMBER = r"[+-]?\d+(?:[.,]\d+)*(?:e[+-]?\d+)?"
_QUANTITY = re.compile(
    rf"(?:(?:[+-]\s*)?{_CURRENCY}\s*)?{_NUMBER}(?:\s*(?:{_UNIT_PATTERN})(?!\w))?"
)
_DATE = re.compile(
    r"(?<!\w)\d{4}-\d{2}-\d{2}"
    r"(?:t\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2}))?(?!\w)"
)
_URL = re.compile(r"\b(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>\"'`]+", re.IGNORECASE)
# 'um'/'uma' não entram: também são artigos. Isso é uma barreira lexical parcial,
# não um analisador semântico de português; o prompt proíbe quantidades por extenso.
_WORD_NUMBER = re.compile(
    r"\b(?:zero|dois|duas|três|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|treze|"
    r"catorze|quatorze|quinze|dezesseis|dezassete|dezessete|dezoito|dezenove|vinte|"
    r"trinta|quarenta|cinquenta|sessenta|setenta|oitenta|noventa|cem|cento|duzentos|"
    r"duzentas|trezentos|trezentas|quatrocentos|quatrocentas|quinhentos|quinhentas|"
    r"seiscentos|seiscentas|setecentos|setecentas|oitocentos|oitocentas|novecentos|"
    r"novecentas|mil|milhão|milhões|bilhão|bilhões|metade|dobro|dobrou|duplicou|triplo|triplicou)\b"
)


class ExplanationValidationError(ValueError):
    """Resposta reprovada por uma restrição verificável; mensagem sem dados brutos."""


class EvidenceContextError(ExplanationValidationError):
    """Contexto do servidor contém estruturas ou metadados inválidos."""


class EvidenceReferenceError(ExplanationValidationError):
    """Citações não pertencem ao contexto ou contradizem a ausência de evidências."""


class UnsupportedClaimError(ExplanationValidationError):
    """Número, data, unidade ou URL do texto não tem suporte nas citações."""


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).replace("−", "-").split()).casefold()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", _normalize(text))


def _date_literals(value: date | datetime) -> set[str]:
    if isinstance(value, datetime):
        return {
            value.date().isoformat(),
            value.isoformat().casefold(),
            value.isoformat().replace("+00:00", "Z").casefold(),
        }
    return {value.isoformat()}


def _supported_dates(context: EvidenceContext, items: list[EvidenceItem]) -> set[str]:
    # Metadados temporais só acompanham evidências efetivamente citadas/resolvidas.
    dates = _date_literals(context.as_of) if items else set()
    for item in items:
        dates.update(_date_literals(item.period.start))
        dates.update(_date_literals(item.period.end))
        source = item.source
        if isinstance(source, AlphaSignalSource):
            for instant in (source.observation_date, source.published_at, source.ingested_at):
                dates.update(_date_literals(instant))
        elif isinstance(source, FinanceRecordSource):
            dates.update(_date_literals(source.recorded_at))
        else:
            dates.update(_date_literals(source.computed_at))
            dates.update(_date_literals(source.input_scope.period.start))
            dates.update(_date_literals(source.input_scope.period.end))
    return dates


def _validate_text(text: str, context: EvidenceContext, items: list[EvidenceItem]) -> None:
    allowed_urls = {
        str(item.source.source_url) for item in items if isinstance(item.source, AlphaSignalSource)
    }

    def mask_url(match: re.Match[str]) -> str:
        token = match.group()
        # Preservar maiúsculas do caminho: URLs não têm comparação case-insensitive.
        candidate = token if token in allowed_urls else token.rstrip(".,;!?)")
        if candidate not in allowed_urls:
            raise UnsupportedClaimError("URL ausente das fontes citadas")
        return " " * len(token)

    working = _normalize(_URL.sub(mask_url, text))
    # Texto numérico de notícia só é aceito como reprodução da passagem original;
    # seus números não viram valores avulsos disponíveis para qualquer afirmação.
    for item in items:
        if isinstance(item.value, TextValue) and any(c.isalpha() for c in item.value.value_text):
            literal = _normalize(item.value.value_text)
            working = re.sub(
                rf"(?<!\w){re.escape(literal)}(?!\w)",
                lambda match: " " * len(match.group()),
                working,
            )
    dates = _supported_dates(context, items)

    def mask_date(match: re.Match[str]) -> str:
        before = working[: match.start()].rstrip()
        after = working[match.end() :].lstrip()
        if (
            match.group() not in dates
            or re.search(rf"{_CURRENCY}$", before)
            or before.endswith(("+", "-"))
            or re.match(rf"(?:{_UNIT_PATTERN})(?!\w)", after)
        ):
            raise UnsupportedClaimError("Data ausente das evidências ou com unidade incompatível")
        if match.end() < len(working) and working[match.end()] in "+-0123456789":
            raise UnsupportedClaimError("Data não reproduz os metadados originais")
        return " " * len(match.group())

    working = _DATE.sub(mask_date, working)
    values = {
        _compact(item.display_value) for item in items if not isinstance(item.value, TextValue)
    }
    # Contagem permite o inteiro isolado; dinheiro e indicadores exigem a unidade.
    values.update(
        str(item.value.value_int) for item in items if isinstance(item.value, IntegerValue)
    )
    for match in _QUANTITY.finditer(working):
        before = working[: match.start()]
        after = working[match.end() :]
        adjacent = (bool(before) and (before[-1].isalnum() or before[-1] in "_+-$€£/.,%")) or (
            bool(after) and (after[0].isalnum() or after[0] in "_%/$€£")
        )
        if (
            adjacent
            or before.rstrip().endswith(("+", "-", "/"))
            or _compact(match.group()) not in values
        ):
            raise UnsupportedClaimError("Valor ou unidade ausente das evidências citadas")
    if _WORD_NUMBER.search(working):
        raise UnsupportedClaimError("Quantidade por extenso não reproduz a apresentação original")


def build_explain_response(context: EvidenceContext, payload: LLMPayload) -> ExplainResponse:
    """Valida metadados e números literais, sem certificar semântica ou causalidade."""
    # Modelos frozen ainda contêm listas mutáveis. Revalidar um snapshot evita que
    # append/model_copy/model_construct burlem os checks feitos na construção.
    try:
        context = EvidenceContext.model_validate(context.model_dump(warnings=False))
    except ValidationError:
        raise EvidenceContextError(
            "Contexto original incompatível com o contrato temporal"
        ) from None
    try:
        payload = LLMPayload.model_validate(
            payload.model_dump(include=set(LLMPayload.model_fields), warnings=False)
        )
    except ValidationError:
        raise EvidenceReferenceError("Resposta incompatível com o contrato de citações") from None
    items = {item.evidence_id: item for item in context.evidences}
    ids = list(payload.evidence_ids)
    if any(key not in items for key in ids):
        raise EvidenceReferenceError("Citação ausente do contexto original")
    limitations = list(dict.fromkeys([*context.temporal_limitations(), *payload.limitations]))
    if not ids and (payload.uncertainty != "alta" or not limitations):
        raise EvidenceReferenceError("Sem citações, informar incerteza alta e limitação")
    # Preservar citações explícitas e incluir as entradas dos cálculos, sem duplicação.
    seen = set(ids)
    for key in ids:
        source = items[key].source
        if isinstance(source, CalculationSource):
            for dependency in source.input_evidence_ids:
                if dependency not in seen:
                    ids.append(dependency)
                    seen.add(dependency)
    cited = [items[key] for key in ids]
    _validate_text(payload.answer, context, cited)
    for limitation in payload.limitations:
        _validate_text(limitation, context, cited)
    return ExplainResponse(
        answer=payload.answer,
        as_of=context.as_of,
        evidences=cited,
        uncertainty=payload.uncertainty,
        limitations=limitations,
    )
