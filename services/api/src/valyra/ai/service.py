"""Orquestra explicações e monta contexto corrente pelo service público de Finance.

Contexto/cliente substituíveis são dependências do servidor, nunca parâmetros do
corpo HTTP. O domínio lexical não certifica a semântica ou causalidade da resposta.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.orm import Session

from valyra.ai import llm_client
from valyra.ai.domain import EvidenceContextError, build_explain_response
from valyra.ai.schemas import (
    EvidenceContext,
    EvidenceItem,
    ExplainRequest,
    ExplainResponse,
    HistoryMessage,
    LLMPayload,
    LLMRequest,
    MoneyValue,
)
from valyra.finance import service as finance_service

LLMClient = Callable[[LLMRequest], LLMPayload]
ContextProvider = Callable[[datetime], EvidenceContext]
Clock = Callable[[], datetime]
_BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
_TRANSACTION_LIMIT = 20
_MISSING_CONTEXT = (
    "O saldo informado é de referência; não há saldo realizado calculado neste contexto.",
    "Resumo de receitas e despesas ainda indisponível.",
    "Projeções de caixa ainda indisponíveis.",
    "Contexto econômico Alpha ainda indisponível.",
)
_UNSAFE_MONEY = (
    "Há valores financeiros incompatíveis com a precisão ou o tipo exigido pelo contrato IA."
)
_AFTER_CUTOFF = "Há registros posteriores ao corte e omitidos deste contexto."
_EMPTY_CONTEXT = "Não foram disponibilizadas evidências elegíveis para esta explicação."


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
    limitations = list(_MISSING_CONTEXT)
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
                label="Movimentação importada",
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
    built_at = _aware(clock())
    if built_at < as_of:
        raise EvidenceContextError("Relógio retrocedeu durante a montagem do contexto")
    return EvidenceContext(
        account_id=account.id,
        as_of=as_of,
        built_at=built_at,
        evidences=evidences,
        limitations=list(dict.fromkeys(limitations)),
    )


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
