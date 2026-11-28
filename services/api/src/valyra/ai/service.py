"""Orquestra explicações e monta contexto corrente pelo service público de Finance.

Contexto/cliente substituíveis são dependências do servidor, nunca parâmetros do
corpo HTTP. O domínio lexical não certifica a semântica ou causalidade da resposta.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.orm import Session

from valyra.ai import llm_client
from valyra.ai.domain import EvidenceContextError, build_explain_response
from valyra.ai.schemas import (
    CalculationSource,
    DecimalValue,
    EvidenceContext,
    EvidenceItem,
    ExplainRequest,
    ExplainResponse,
    HistoryMessage,
    LLMPayload,
    LLMRequest,
    MoneyValue,
    TextValue,
)
from valyra.alpha import news_service
from valyra.alpha import service as alpha_service
from valyra.core.errors import AppError
from valyra.finance import service as finance_service

LLMClient = Callable[[LLMRequest], LLMPayload]
ContextProvider = Callable[[datetime], EvidenceContext]
Clock = Callable[[], datetime]
_BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
_TRANSACTION_LIMIT = 20
_NO_ALPHA = "Contexto econômico Alpha sem coletas publicadas até o corte."
_ALPHA_NOT_CAUSE = (
    "Indicadores econômicos e gastos aparecem juntos no contexto; isso não demonstra causa."
)
# Último e penúltimo ponto de cada série bastam para "subiu ou caiu" sem o LLM calcular.
_ALPHA_POINTS = 2
# Mesmo teto de EvidenceContext.evidences (ai/schemas.py). Hoje o Finance ocupa no máximo
# ~71 itens e o Alpha 26 (13 séries x 2); o corte explícito impede que o teto vire erro.
_EVIDENCE_CAP = 100
_ALPHA_TRIMMED = "Parte dos indicadores Alpha ficou fora do contexto pelo limite de evidências."
_ALPHA_ESTIMATED = (
    "Parte dos indicadores Alpha tem publicação reconstituída na carga histórica (estimada)."
)
_NO_CALCULATIONS = (
    "Sem lote de importação concluído: resumo, orçamento e projeção não foram calculados."
)
_FUTURE_BUSINESS_DAY = (
    "A data de negócio do Finance é posterior ao corte; cálculos do Finance omitidos."
)
_NO_PROJECTION = "Projeção de caixa indisponível para esta conta."
_CHANGED_AFTER_CUTOFF = (
    "Houve alterações no Finance depois do corte; cálculos omitidos para não antecipar dados."
)
_BUDGET_TRIMMED = "Orçamento parcial: só as categorias mais pressionadas entram no contexto."
# Três evidências por categoria orçada: oito categorias mantêm o contexto abaixo de 100 itens.
_BUDGET_LIMIT = 8
_BUDGET_PRIORITY = {"over": 0, "warning": 1, "ok": 2}
# Poucas categorias bastam para explicar o mês sem estourar o teto de 100 evidências.
_CATEGORY_LIMIT = 8
_PROJECTION_DAYS = 30
_METHOD_VERSION = "adr-0010"
_BUDGET_STATUS_TEXT = {
    "ok": "dentro do limite",
    "warning": "em atenção, perto do limite",
    "over": "acima do limite",
}
_UNSAFE_MONEY = (
    "Há valores financeiros incompatíveis com a precisão ou o tipo exigido pelo contrato IA."
)
_AFTER_CUTOFF = "Há registros posteriores ao corte e omitidos deste contexto."
_EMPTY_CONTEXT = "Não foram disponibilizadas evidências elegíveis para esta explicação."
_PROMPT_TRIMMED = "Contexto parcial: evidências omitidas para respeitar o limite de tamanho."
_HISTORY_TRIMMED = "Parte do histórico de conversa foi omitida pelo limite de tamanho."


@dataclass(frozen=True)
class _AccountSnapshot:
    id: UUID
    balance_cents: int
    balance_as_of: date
    recorded_at: datetime


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceContextError("Relógio ou timestamp do servidor sem fuso válido")
    return value.astimezone(UTC)


def _snapshot(context: EvidenceContext) -> EvidenceContext:
    if not isinstance(context, EvidenceContext):
        raise EvidenceContextError("O provedor deve retornar um contexto IA tipado")
    try:
        return EvidenceContext.model_validate(context.model_dump(warnings=False))
    except ValidationError:
        raise EvidenceContextError("Contexto do servidor incompatível com o contrato IA") from None


def _bounded_request(request: LLMRequest) -> LLMRequest:
    """Remove itens inteiros; o snapshot de validação terá só o que o LLM recebeu."""
    context = request.context_data
    items = list(context.evidences)
    history = list(request.history)
    # Preserva avisos temporais mesmo se a evidência que os motivou precisar sair.
    limitations = list(context.limitations)

    def record(message: str) -> None:
        if not any(message in entry for entry in limitations):
            if len(limitations) < 20:
                limitations.append(message)
            else:
                # Não descartar um aviso existente para abrir espaço para o corte.
                for i, entry in enumerate(limitations):
                    if len(entry) + len(message) + 1 <= 2000:
                        limitations[i] = f"{entry} {message}"
                        break
                else:
                    raise llm_client.LLMPromptError("Sem espaço para registrar contexto parcial")

    while True:
        try:
            llm_client.validate_prompt_size(request)
            return request
        except llm_client.LLMPromptError:
            for message in context.temporal_limitations():
                record(message)
            if history:
                history.pop(0)
                record(_HISTORY_TRIMMED)
            elif items:
                dependencies = {
                    key
                    for item in items
                    if isinstance(item.source, CalculationSource)
                    for key in item.source.input_evidence_ids
                }

                # Resumos, limites e projeções têm precedência sobre exemplos de
                # transações. Só folhas saem, para nunca deixar um cálculo órfão.
                def priority(item: EvidenceItem) -> int:
                    if item.metric_key == "finance.transaction.amount":
                        return 3
                    if item.metric_key in {"finance.month.category_total", "finance.budget.status"}:
                        return 2
                    return 1 if item.source.kind == "alpha_signal" else 0

                removable = [
                    i for i, item in enumerate(items) if item.evidence_id not in dependencies
                ]
                index = max(removable, key=lambda i: (priority(items[i]), i))
                items.pop(index)
                record(_PROMPT_TRIMMED)
            else:
                # Pergunta/avisos também têm limites; não esconder erro estrutural
                # nem enviar ao provedor um pedido que continua grande demais.
                raise
        context = EvidenceContext.model_validate(
            context.model_dump() | {"evidences": items, "limitations": limitations}
        )
        request = LLMRequest(question=request.question, context_data=context, history=history)


def explain_with_context(
    request: ExplainRequest,
    context: EvidenceContext,
    *,
    client: LLMClient | None = None,
    history: Sequence[HistoryMessage] = (),
) -> ExplainResponse:
    """Executa contexto já autorizado pelo chamador; não consulta ou autoriza contas."""
    request = ExplainRequest.model_validate(request.model_dump(warnings=False))
    original = _snapshot(context)
    if original.account_id != request.account_id:
        raise EvidenceContextError("Conta da pergunta difere da conta do contexto")
    # O cliente recebe outra cópia: nem um cliente substituto pode adulterar o
    # snapshot contra o qual a resposta será validada.
    llm_request = LLMRequest(
        question=request.question,
        context_data=_snapshot(original),
        history=list(history),
    )
    if original.evidences:
        llm_request = _bounded_request(llm_request)
        original = _snapshot(llm_request.context_data)
    if not original.evidences:
        # Ausência de dados tem resposta determinística; não pagar ao LLM para inferir zero.
        result = LLMPayload(
            answer=(
                "Não há evidências suficientes neste contexto para explicar a situação financeira."
            ),
            evidence_ids=[],
            uncertainty="alta",
            limitations=[_EMPTY_CONTEXT],
        )
    else:
        invoke = llm_client.call_llm if client is None else client
        result = invoke(llm_request)
        if not isinstance(result, LLMPayload):
            raise llm_client.LLMParseError("Cliente retornou uma resposta fora do contrato IA")
    return build_explain_response(original, result)


def _money(value: int, limitations: list[str]) -> MoneyValue | None:
    try:
        return MoneyValue(amount_cents=value)
    except ValidationError:
        # Não arredondar nem substituir por zero quando BIGINT excede a precisão do frontend.
        limitations.append(_UNSAFE_MONEY)
        return None


def _finance_context(
    session: Session,
    user_id: UUID,
    account: _AccountSnapshot,
    as_of: datetime,
    clock: Clock,
) -> EvidenceContext:
    evidences: list[EvidenceItem] = []
    limitations: list[str] = []
    today = as_of.astimezone(_BUSINESS_ZONE).date()
    if _aware(account.recorded_at) > as_of:
        limitations.append(_AFTER_CUTOFF)
    elif account.balance_as_of > today:
        limitations.append("O saldo de referência está datado após o corte e não foi incluído.")
    elif (value := _money(account.balance_cents, limitations)) is not None:
        evidences.append(
            EvidenceItem(
                evidence_id="account_reference_balance",
                metric_key="finance.account.reference_balance",
                label="Saldo de referência informado",
                basis="reference",
                source={
                    "kind": "finance_record",
                    "record_type": "account",
                    "record_id": account.id,
                    "recorded_at": account.recorded_at,
                },
                value=value,
                period={"start": account.balance_as_of, "end": account.balance_as_of},
            )
        )

    rows, total = finance_service.list_transactions(
        session,
        user_id,
        account_id=account.id,
        date_from=None,
        date_to=today,
        category_id=None,
        # Sem filtro de sinais: o contexto da IA lê as movimentações recentes como estão.
        is_recurring=None,
        is_anomaly=None,
        limit=_TRANSACTION_LIMIT,
        offset=0,
    )
    selected = rows[:_TRANSACTION_LIMIT]
    if total > len(selected) or len(rows) > len(selected):
        limitations.append(
            "Histórico parcial: o contexto não inclui todas as movimentações da conta."
        )
    included = 0
    for transaction, _category in selected:
        if transaction.account_id != account.id:
            raise EvidenceContextError("Consulta Finance retornou transação de outra conta")
        if transaction.date > today or _aware(transaction.updated_at) > as_of:
            limitations.append(_AFTER_CUTOFF)
            continue
        value = _money(transaction.amount_cents, limitations)
        if value is None:
            continue
        # Sem descrição/nome livre: o contexto precisa apenas dos valores e origem
        # para este recorte; não enviar texto desnecessário do extrato ao provedor.
        evidences.append(
            EvidenceItem(
                evidence_id=f"tx_{transaction.id.hex}",
                metric_key="finance.transaction.amount",
                label=_transaction_label(transaction, _category),
                basis="observed",
                source={
                    "kind": "finance_record",
                    "record_type": "transaction",
                    "record_id": transaction.id,
                    "recorded_at": transaction.updated_at,
                    "import_batch_id": transaction.import_batch_id,
                },
                value=value,
                period={"start": transaction.date, "end": transaction.date},
            )
        )
        included += 1
    if not included:
        limitations.append("Nenhuma movimentação elegível foi incluída neste contexto.")
    evidences.extend(_calculation_evidences(session, user_id, account, as_of, clock, limitations))
    room = _EVIDENCE_CAP - len(evidences)
    evidences.extend(_alpha_evidences(session, as_of, limitations, room))
    evidences.extend(_news_evidences(session, as_of, limitations, _EVIDENCE_CAP - len(evidences)))
    built_at = _aware(clock())
    if built_at < as_of:
        raise EvidenceContextError("Relógio retrocedeu durante a montagem do contexto")
    return EvidenceContext(
        account_id=account.id,
        as_of=as_of,
        built_at=built_at,
        evidences=evidences,
        limitations=_cap_limitations(limitations),
    )


def _cap_limitations(entries: Sequence[str]) -> list[str]:
    """Deduplica e mantém até 20 itens (teto do contrato), concatenando excedentes sem perda."""
    merged: list[str] = []
    for message in dict.fromkeys(entries):
        if len(merged) < 20:
            merged.append(message)
            continue
        for i in range(len(merged) - 1, -1, -1):
            if len(merged[i]) + len(message) + 1 <= 2000:
                merged[i] = f"{merged[i]} {message}"
                break
    return merged


def _transaction_label(transaction: object, category: object) -> str:
    # Categoria e sinais ajudam a explicar o mês; a descrição livre do extrato continua fora.
    parts = ["Movimentação importada"]
    name = getattr(category, "name", None)
    if name:
        parts.append(name)
    if getattr(transaction, "is_recurring", False):
        parts.append("recorrente")
    if finance_service.is_anomalous(transaction):
        parts.append("atípica")
    return " · ".join(parts)


def _previous_month(month: str) -> str:
    year, number = (int(part) for part in month.split("-"))
    year, number = (year - 1, 12) if number == 1 else (year, number - 1)
    return f"{year:04d}-{number:02d}"


def _alpha_evidences(
    session: Session, as_of: datetime, limitations: list[str], room: int = _EVIDENCE_CAP
) -> list[EvidenceItem]:
    """Indicadores Alpha publicados até o corte, com procedência completa (ADR-0011/0012)."""
    radar = alpha_service.get_radar(session, as_of)
    items: list[EvidenceItem] = []
    model = radar.soy_volatility
    if model.status == "insufficient_data":
        if radar.indicators:
            limitations.append(
                "Estudo de oscilação da cadeia da soja sem histórico alinhado "
                "suficiente até o corte."
            )
    elif radar.model_record_ids:
        limitations.append(
            "Estudo de oscilação da cadeia da soja: janela curta experimental; mede amplitude "
            "de risco, não probabilidade de alta/queda nem recomendação."
        )
        if any("não superou" in item for item in model.limitations):
            limitations.append(
                "O modelo com clima não superou o modelo de mercado no erro "
                "walk-forward desta janela."
            )
        # A síntese não pode fazer uma reconstituição parecer um backtest ao vivo.
        for warning in model.limitations:
            if "Publicações estimadas" in warning:
                limitations.append(warning)
        cutoff_day = as_of.astimezone(_BUSINESS_ZONE).date()
        span = {"start": model.first_observation_date, "end": model.last_observation_date}
        for key, value, unit, basis in (
            ("m1_5d", model.m1_forecast_pct, "%", "projected"),
            ("m0_5d", model.m0_forecast_pct, "%", "projected"),
            ("mae_m1", model.mae_m1_pp, "pp", "observed"),
            ("mae_m0", model.mae_m0_pp, "pp", "observed"),
        ):
            if (
                basis == "projected"
                and model.last_observation_date + timedelta(days=7) <= cutoff_day
            ):
                limitations.append("Estimativa da soja defasada: horizonte projetado já passou.")
                continue
            items.append(
                EvidenceItem(
                    evidence_id=f"soy_{key}",
                    metric_key=f"alpha.volatility.slce3.{key}",
                    label={
                        "m1_5d": "Oscilação estimada pelo modelo com clima",
                        "m0_5d": "Oscilação estimada pelo modelo de mercado",
                        "mae_m1": "Erro walk-forward do modelo com clima",
                        "mae_m0": "Erro walk-forward do modelo de mercado",
                    }[key],
                    basis=basis,
                    source={
                        "kind": "calculation",
                        "module": "alpha",
                        "method_key": "alpha.soy_volatility_ridge",
                        "method_version": "adr-0014-v1",
                        "computed_at": as_of,
                        "input_scope": {
                            "account_id": None,
                            "period": span,
                            "record_ids": radar.model_record_ids,
                        },
                    },
                    value=DecimalValue(value_decimal=value, unit=unit),
                    period=(
                        {
                            "start": cutoff_day + timedelta(days=1),
                            "end": cutoff_day + timedelta(days=7),
                        }
                        if basis == "projected"
                        else span
                    ),
                )
            )
    # Último ponto de todas as séries antes dos anteriores: se faltar espaço, sai o histórico.
    ranked = [
        (view, point)
        for depth in range(1, _ALPHA_POINTS + 1)
        for view in radar.indicators
        if len(view.history) >= depth
        for point in (view.history[-depth],)
    ]
    for view, point in ranked:
        items.append(
            EvidenceItem(
                evidence_id=f"alpha_{point.signal_id.hex}",
                metric_key=view.series.metric_key,
                label=f"{view.series.title}, em {view.series.unit_label}",
                basis="observed",
                source={
                    "kind": "alpha_signal",
                    "source_id": view.source.id,
                    "signal_id": point.signal_id,
                    "signal_key": point.signal_key,
                    "revision_id": point.revision_id,
                    "source_url": point.source_url,
                    "observation_date": point.observation_date,
                    "published_at": point.published_at,
                    "published_at_estimated": point.published_at_estimated,
                    "ingested_at": point.ingested_at,
                },
                value=DecimalValue(
                    value_decimal=alpha_service.format_value(point.value), unit=view.series.unit
                ),
                period={"start": point.observation_date, "end": point.observation_date},
            )
        )
    if len(items) > room:
        limitations.append(_ALPHA_TRIMMED)
        items = items[: max(room, 0)]
    if items:
        limitations.append(_ALPHA_NOT_CAUSE)
        if any(getattr(item.source, "published_at_estimated", False) for item in items):
            limitations.append(_ALPHA_ESTIMATED)
    else:
        limitations.append(_NO_ALPHA)
    return items


# Manchetes da semana: poucas bastam para o resumo e mantêm o prompt bem abaixo do teto.
_NEWS_LIMIT = 8
_NEWS_RULE = (
    "Notícias entram só como manchete, com fonte e data; o tema ligado ao orçamento vem da "
    "regra news_theme_v3 e indica o que pode mudar, não causa nem previsão."
)


def _news_evidences(
    session: Session, as_of: datetime, limitations: list[str], room: int
) -> list[EvidenceItem]:
    """Manchetes da semana até o corte (proposta da ADR-0013), como evidência textual."""
    report = news_service.get_weekly_report(session, as_of)
    # Uma manchete de cada tema primeiro, para o resumo cobrir a semana e não um tema só.
    rounds = max((len(view.items) for view in report.themes), default=0)
    ordered = [
        (view.theme, view.items[index])
        for index in range(rounds)
        for view in report.themes
        if index < len(view.items)
    ]
    items = [
        EvidenceItem(
            evidence_id=f"news_{item.signal_id.hex}",
            metric_key=f"alpha.news.{theme.key}",
            label=(
                f"Manchete sobre {theme.title.lower()}, de {item.source.name}"
                + (f", cita {', '.join(item.tickers)}" if item.tickers else "")
            ),
            basis="observed",
            source={
                "kind": "alpha_signal",
                "source_id": item.source.id,
                "signal_id": item.signal_id,
                "signal_key": item.signal_key,
                "revision_id": item.revision_id,
                "source_url": item.url,
                "observation_date": item.observation_date,
                "published_at": item.published_at,
                "published_at_estimated": False,
                "ingested_at": item.ingested_at,
            },
            value=TextValue(value_text=item.title),
            period={"start": item.observation_date, "end": item.observation_date},
        )
        for theme, item in ordered[: min(_NEWS_LIMIT, max(room, 0))]
    ]
    if items:
        limitations.append(_NEWS_RULE)
    return items


def _calculation_evidences(
    session: Session,
    user_id: UUID,
    account: _AccountSnapshot,
    as_of: datetime,
    clock: Clock,
    limitations: list[str],
) -> list[EvidenceItem]:
    """Resultados já calculados pelo Finance; o LLM só cita, nunca refaz as contas.

    Cada cálculo aponta os lotes concluídos até o corte, para a procedência ser auditável.
    """
    cutoff_day = as_of.astimezone(_BUSINESS_ZONE).date()
    batches = [
        batch_id
        for batch_id, completed_at in finance_service.list_completed_import_batches(
            session, user_id, account.id
        )
        if completed_at is not None and _aware(completed_at) <= as_of
    ]
    if not batches:
        limitations.append(_NO_CALCULATIONS)
        return []
    # Os services do Finance leem o estado corrente; se algo mudou após o corte, os totais
    # já incluiriam essa mudança. Omitir é a única forma de não vazar dados futuros.
    last_change = finance_service.get_last_change_at(session, user_id, account.id)
    if last_change is not None and _aware(last_change) > as_of:
        limitations.append(_CHANGED_AFTER_CUTOFF)
        return []
    summary = finance_service.get_summary(session, user_id, account.id, None)
    if summary.today > cutoff_day:
        # Um DEMO_TODAY no futuro anteciparia dados que o corte ainda não conhece.
        limitations.append(_FUTURE_BUSINESS_DAY)
        return []
    previous = finance_service.get_summary(
        session, user_id, account.id, _previous_month(summary.month)
    )
    budget = finance_service.get_account_budget_report(session, user_id, account.id, None)
    try:
        projection = finance_service.get_projection(
            session, user_id, account.id, _PROJECTION_DAYS
        ).projection
    except AppError as error:
        # Só a ausência esperada de saldo de partida vira limitação; o resto propaga.
        if error.code != "BALANCE_UNAVAILABLE":
            raise
        projection = None
    computed_at = _aware(clock())
    items: list[EvidenceItem] = []

    def period(start: date, end: date) -> dict[str, date]:
        return {"start": start, "end": end}

    def add(evidence_id, metric_key, label, basis, method, span, value) -> None:
        if isinstance(value, int):
            value = _money(value, limitations)
            if value is None:
                return
        items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                metric_key=metric_key,
                label=label,
                basis=basis,
                source={
                    "kind": "calculation",
                    "module": "finance",
                    "method_key": method,
                    "method_version": _METHOD_VERSION,
                    "computed_at": computed_at,
                    "input_scope": {
                        "account_id": account.id,
                        "period": span,
                        "import_batch_ids": batches,
                    },
                },
                value=value,
                period=span,
            )
        )

    month_first = date(*(int(part) for part in summary.month.split("-")), 1)
    month_span = period(month_first, summary.today)
    if summary.realized_balance_cents is not None:
        add(
            "finance_realized_balance",
            "finance.balance.realized",
            "Saldo realizado: referência somada às movimentações até hoje",
            "observed",
            "finance.realized_balance",
            period(min(account.balance_as_of, summary.today), summary.today),
            summary.realized_balance_cents,
        )
    month = summary.month_summary
    for key, label, cents in (
        ("income", "Entradas do mês até hoje", month.income_cents),
        ("expenses", "Saídas do mês até hoje", month.expenses_cents),
        ("net", "Resultado do mês até hoje", month.net_cents),
    ):
        add(
            f"month_{key}",
            f"finance.month.{key}",
            label,
            "observed",
            "finance.month_summary",
            month_span,
            cents,
        )
    for total in month.categories[:_CATEGORY_LIMIT]:
        name = summary.categories[total.category_id].name
        add(
            f"month_cat_{total.category_id.hex}",
            "finance.month.category_total",
            f"Total do mês até hoje em {name}",
            "observed",
            "finance.month_summary",
            month_span,
            total.total_cents,
        )

    prev_month = previous.month_summary
    if prev_month.categories:
        prev_first = date(*(int(part) for part in previous.month.split("-")), 1)
        # O mês anterior está fechado: vai do dia 1 ao último dia, antes do mês corrente.
        prev_span = period(prev_first, month_first - timedelta(days=1))
        add(
            "prev_month_expenses",
            "finance.month.expenses",
            "Saídas do mês anterior",
            "observed",
            "finance.month_summary",
            prev_span,
            prev_month.expenses_cents,
        )
        for total in prev_month.categories[:_CATEGORY_LIMIT]:
            name = previous.categories[total.category_id].name
            add(
                f"prev_cat_{total.category_id.hex}",
                "finance.month.category_total",
                f"Total do mês anterior em {name}",
                "observed",
                "finance.month_summary",
                prev_span,
                total.total_cents,
            )

    lines = sorted(
        budget.lines,
        key=lambda line: (_BUDGET_PRIORITY[line.status], -line.spent_cents, line.category.name),
    )
    if len(lines) > _BUDGET_LIMIT:
        limitations.append(_BUDGET_TRIMMED)
    for line in lines[:_BUDGET_LIMIT]:
        hex_id = line.category.id.hex
        name = line.category.name
        add(
            f"budget_limit_{hex_id}",
            "finance.budget.limit",
            f"Limite mensal definido para {name}",
            "reference",
            "finance.budget_report",
            month_span,
            line.limit_cents,
        )
        add(
            f"budget_spent_{hex_id}",
            "finance.budget.spent",
            f"Gasto do mês até hoje em {name}, comparado ao limite",
            "observed",
            "finance.budget_report",
            month_span,
            line.spent_cents,
        )
        add(
            f"budget_status_{hex_id}",
            "finance.budget.status",
            f"Situação do orçamento de {name}",
            "observed",
            "finance.budget_report",
            month_span,
            TextValue(value_text=_BUDGET_STATUS_TEXT[line.status]),
        )

    if budget.daily_allowance_cents is not None:
        add(
            "budget_daily_allowance",
            "finance.budget.daily_allowance",
            "Limite diário do orçamento desta conta até o fim do mês; não é saldo disponível",
            "reference",
            "finance.budget_report",
            month_span,
            budget.daily_allowance_cents,
        )
    else:
        limitations.append(
            "Limite diário indisponível: sem tetos de orçamento ou período já encerrado."
        )

    # Só dias depois do corte são futuros: com DEMO_TODAY anterior ao relógio real,
    # os primeiros dias da série já não são projeção e ficam fora.
    future = [day for day in projection.items if day.date > cutoff_day] if projection else []
    if future:
        horizon = period(future[0].date, future[-1].date)
        end = future[-1]
        add(
            "projection_end_balance",
            "finance.projection.balance",
            "Saldo previsto ao fim do horizonte de projeção",
            "projected",
            "finance.cash_projection",
            period(end.date, end.date),
            end.balance_cents,
        )
        lowest = min(future, key=lambda day: day.balance_cents)
        add(
            "projection_min_balance",
            "finance.projection.min_balance",
            "Menor saldo previsto no horizonte de projeção",
            "projected",
            "finance.cash_projection",
            period(lowest.date, lowest.date),
            lowest.balance_cents,
        )
        add(
            "projection_variable_daily",
            "finance.projection.variable_daily",
            "Premissa: gasto variável diário estimado pela média recente",
            "projected",
            "finance.cash_projection",
            horizon,
            projection.variable_daily_cents,
        )
    else:
        limitations.append(_NO_PROJECTION)
    return items


def explain_for_account(
    session: Session,
    user_id: UUID,
    request: ExplainRequest,
    *,
    client: LLMClient | None = None,
    context_provider: ContextProvider | None = None,
    clock: Clock = _utc_now,
    history: Sequence[HistoryMessage] = (),
) -> ExplainResponse:
    """Autoriza via Finance antes de chamar qualquer produtor de contexto ou LLM.

    O produtor opcional é uma dependência interna que recebe o corte do servidor;
    permite integrar novos services sem alterar a orquestração/validação.
    """
    request = ExplainRequest.model_validate(request.model_dump(warnings=False))
    account = finance_service.get_account_for_user(session, user_id, request.account_id)
    if account.id != request.account_id:
        raise EvidenceContextError("Consulta Finance retornou uma conta diferente da solicitada")
    as_of = _aware(clock())
    if context_provider is None:
        account_data = _AccountSnapshot(
            account.id, account.balance_cents, account.balance_as_of, account.updated_at
        )
        context = _finance_context(session, user_id, account_data, as_of, clock)
    else:
        context = _snapshot(context_provider(as_of))
        if context.as_of != as_of or context.built_at > _aware(clock()):
            raise EvidenceContextError("Provedor de contexto não respeitou o corte do servidor")
    # Esta operação só lê: não fazer commit/rollback da sessão pertencente ao chamador.
    return explain_with_context(request, context, client=client, history=history)
