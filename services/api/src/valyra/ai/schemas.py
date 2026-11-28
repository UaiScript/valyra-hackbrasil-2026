"""Contratos da ADR-0011: entrada pública, contexto do servidor e saída do modelo.

Estes schemas não autorizam contas nem conferem números no texto. O serviço autoriza a
conta e o domínio confere os literais do texto antes de publicar uma explicação;
essa checagem não comprova semântica, causalidade ou veracidade externa.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    StrictInt,
    StringConstraints,
    model_validator,
)

JSON_SAFE_INTEGER = 2**53 - 1
_BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
_ESTIMATED_PUBLICATION = "Publicação estimada: reconstituição ilustrativa."
_LATE_INGESTION = "Fonte ingerida após o corte: reconstituição por publicação."


def _safe_integer(value: int) -> int:
    # Não usar float nem alterar o BIGINT dos endpoints Finance existentes.
    if not -JSON_SAFE_INTEGER <= value <= JSON_SAFE_INTEGER:
        raise ValueError("Inteiro fora da faixa exata do JSON no frontend")
    return value


def _iso_instant(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("Instante deve ser datetime ou texto ISO 8601 com fuso")


def _iso_date(value: object) -> date:
    if type(value) is date:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("Data de negócio deve usar AAAA-MM-DD")


def _uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        return UUID(value)
    raise ValueError("Identificador deve ser UUID canônico")


SafeInteger = Annotated[StrictInt, AfterValidator(_safe_integer)]
UtcInstant = Annotated[
    AwareDatetime, BeforeValidator(_iso_instant), AfterValidator(lambda v: v.astimezone(UTC))
]
BusinessDate = Annotated[date, BeforeValidator(_iso_date)]
Identifier = Annotated[UUID, BeforeValidator(_uuid)]
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
EvidenceId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
DecimalText = Annotated[
    str, StringConstraints(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$", max_length=256)
]
Uncertainty = Literal["baixa", "média", "alta"]
# Vocabulário do recorte não monetário. Adaptadores futuros devem registrar novas unidades.
NonMonetaryUnit = Literal[
    "%", "pp", "fraction", "count", "t", "kg", "ha", "kg/ha", "t/ha", "mm", "°C", "index"
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class EvidencePeriod(ContractModel):
    start: BusinessDate
    end: BusinessDate

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("Período invertido")
        return self


class MoneyValue(ContractModel):
    kind: Literal["money"] = "money"
    amount_cents: SafeInteger
    currency: Literal["BRL"] = "BRL"


class IntegerValue(ContractModel):
    kind: Literal["integer"] = "integer"
    value_int: SafeInteger
    unit: Literal["count"] = "count"


class DecimalValue(ContractModel):
    kind: Literal["decimal"] = "decimal"
    value_decimal: DecimalText
    unit: NonMonetaryUnit


class TextValue(ContractModel):
    kind: Literal["text"] = "text"
    value_text: NonBlank


EvidenceValue = Annotated[
    MoneyValue | IntegerValue | DecimalValue | TextValue, Field(discriminator="kind")
]


class FinanceRecordSource(ContractModel):
    kind: Literal["finance_record"] = "finance_record"
    record_type: Literal["account", "transaction"]
    record_id: Identifier
    recorded_at: UtcInstant
    import_batch_id: Identifier | None = None

    @model_validator(mode="after")
    def _batch(self) -> Self:
        if self.record_type == "transaction" and self.import_batch_id is None:
            raise ValueError("Transação exige o lote de importação")
        if self.record_type == "account" and self.import_batch_id is not None:
            raise ValueError("Conta não referencia lote de transações")
        return self


class CalculationInputScope(ContractModel):
    account_id: Identifier | None = None
    period: EvidencePeriod
    import_batch_ids: list[Identifier] = Field(default_factory=list)
    record_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def _traceable(self) -> Self:
        if not self.import_batch_ids and not self.record_ids:
            raise ValueError("Cálculo exige referências aos registros ou lotes de entrada")
        if len(set(self.import_batch_ids)) != len(self.import_batch_ids):
            raise ValueError("Lotes de entrada duplicados")
        if len(set(self.record_ids)) != len(self.record_ids):
            raise ValueError("Registros de entrada duplicados")
        return self


class CalculationSource(ContractModel):
    kind: Literal["calculation"] = "calculation"
    module: Literal["finance", "alpha"]
    method_key: NonBlank
    method_version: NonBlank
    computed_at: UtcInstant
    input_scope: CalculationInputScope
    input_evidence_ids: list[EvidenceId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _account(self) -> Self:
        if self.module == "finance" and self.input_scope.account_id is None:
            raise ValueError("Cálculo Finance exige a conta no escopo")
        if len(set(self.input_evidence_ids)) != len(self.input_evidence_ids):
            raise ValueError("Dependências de cálculo duplicadas")
        return self


class AlphaSignalSource(ContractModel):
    kind: Literal["alpha_signal"] = "alpha_signal"
    source_id: Identifier
    signal_id: Identifier
    signal_key: NonBlank
    revision_id: Annotated[StrictInt, Field(ge=1)]
    source_url: HttpUrl
    observation_date: BusinessDate
    published_at: UtcInstant
    published_at_estimated: bool
    ingested_at: UtcInstant


EvidenceSource = Annotated[
    FinanceRecordSource | CalculationSource | AlphaSignalSource, Field(discriminator="kind")
]


class EvidenceItem(ContractModel):
    evidence_id: EvidenceId
    metric_key: NonBlank
    label: NonBlank
    basis: Literal["reference", "observed", "projected"]
    source: EvidenceSource
    value: EvidenceValue
    period: EvidencePeriod

    @model_validator(mode="after")
    def _compatible(self) -> Self:
        source = self.source
        is_finance = isinstance(source, FinanceRecordSource) or (
            isinstance(source, CalculationSource) and source.module == "finance"
        )
        prefix = "finance." if is_finance else "alpha."
        if not self.metric_key.startswith(prefix):
            raise ValueError("Métrica incompatível com o módulo de origem")
        if isinstance(self.value, MoneyValue) and not is_finance:
            raise ValueError("Dinheiro Alpha não pertence ao contrato aprovado")
        if isinstance(source, FinanceRecordSource):
            if source.record_type == "account" and isinstance(self.value, MoneyValue):
                if self.basis != "reference":
                    raise ValueError("Saldo informado na conta é referência, não saldo calculado")
            if source.record_type == "transaction" and self.basis != "observed":
                raise ValueError("Transação importada é observada, não projetada ou referência")
        if self.basis == "projected" and not isinstance(source, CalculationSource):
            raise ValueError("Projeção exige método de cálculo identificado")
        return self

    @property
    def display_value(self) -> str:
        """Dica de apresentação do prompt; não é um campo da resposta pública."""
        value = self.value
        if isinstance(value, MoneyValue):
            magnitude = abs(value.amount_cents)
            whole = f"{magnitude // 100:,}".replace(",", ".")
            sign = "-" if value.amount_cents < 0 else ""
            return f"R$ {sign}{whole},{magnitude % 100:02}"
        if isinstance(value, DecimalValue):
            return f"{value.value_decimal.replace('.', ',')} {value.unit}"
        if isinstance(value, IntegerValue):
            return f"{value.value_int} {value.unit}"
        return value.value_text


class EvidenceContext(ContractModel):
    account_id: Identifier
    as_of: UtcInstant
    built_at: UtcInstant
    evidences: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    limitations: list[NonBlank] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.as_of > self.built_at:
            raise ValueError("Corte posterior à montagem do contexto")
        items = {item.evidence_id: item for item in self.evidences}
        if len(items) != len(self.evidences):
            raise ValueError("IDs de evidências duplicados")
        signal_keys: set[str] = set()
        for item in self.evidences:
            source = item.source
            if isinstance(source, FinanceRecordSource):
                if source.recorded_at > self.as_of:
                    raise ValueError("Registro Finance posterior ao corte")
                if source.record_type == "account" and source.record_id != self.account_id:
                    raise ValueError("Registro de conta fora do contexto")
            elif isinstance(source, AlphaSignalSource):
                if source.published_at > self.as_of or source.ingested_at > self.built_at:
                    raise ValueError("Sinal fora do corte ou ingerido após a montagem")
                if source.signal_key in signal_keys:
                    raise ValueError("Mais de uma revisão do mesmo sinal no contexto")
                signal_keys.add(source.signal_key)
            else:
                if source.computed_at > self.built_at:
                    raise ValueError("Cálculo posterior à montagem do contexto")
                if source.input_scope.account_id not in (None, self.account_id):
                    raise ValueError("Escopo de cálculo pertence a outra conta")
                if any(key not in items for key in source.input_evidence_ids):
                    raise ValueError("Dependência de cálculo ausente do contexto")
            if (
                item.basis == "projected"
                and item.period.start <= self.as_of.astimezone(_BUSINESS_ZONE).date()
            ):
                raise ValueError("Período projetado deve começar após o corte")
        # O grafo é pequeno e limitado pelo contexto; DFS também detecta autorreferência.
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visiting:
                raise ValueError("Dependência cíclica entre evidências")
            if key in visited:
                return
            visiting.add(key)
            source = items[key].source
            if isinstance(source, CalculationSource):
                for dependency in source.input_evidence_ids:
                    visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in items:
            visit(key)
        return self

    def temporal_limitations(self) -> list[str]:
        limitations = list(self.limitations)
        for item in self.evidences:
            source = item.source
            if isinstance(source, AlphaSignalSource):
                if source.published_at_estimated:
                    limitations.append(_ESTIMATED_PUBLICATION)
                if source.ingested_at > self.as_of:
                    limitations.append(_LATE_INGESTION)
        return list(dict.fromkeys(limitations))


class ExplainRequest(ContractModel):
    """Entrada HTTP: contexto e identidade do usuário não vêm do navegador."""

    question: NonBlank
    account_id: Identifier


class HistoryMessage(ContractModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class LLMRequest(ContractModel):
    """Somente o servidor monta este contrato interno, após autorizar a conta."""

    question: NonBlank
    context_data: EvidenceContext
    history: list[HistoryMessage] = Field(default_factory=list, max_length=10)


class LLMPayload(ContractModel):
    """O provedor devolve citações, sem poder sobrescrever dados de origem."""

    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    evidence_ids: list[EvidenceId] = Field(max_length=100)
    uncertainty: Uncertainty
    limitations: list[NonBlank] = Field(max_length=20)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Citações duplicadas")
        return self


class LLMResponse(LLMPayload):
    """Metadados internos atribuídos pela aplicação; não é a resposta HTTP."""

    provider: Literal["gemini", "groq", "openrouter", "openai"]
    model: NonBlank


class ExplainResponse(ContractModel):
    """Resposta HTTP montada com as evidências originais do servidor."""

    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    as_of: UtcInstant
    evidences: list[EvidenceItem]
    uncertainty: Uncertainty
    limitations: list[NonBlank]
