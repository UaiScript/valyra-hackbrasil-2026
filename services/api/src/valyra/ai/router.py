"""HTTP IA: contexto do servidor, resposta validada e erros sem conteúdo do provedor."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.orm import Session

from valyra.ai import service
from valyra.ai.domain import EvidenceContextError, ExplanationValidationError
from valyra.ai.llm_client import (
    LLMConfigurationError,
    LLMParseError,
    LLMPromptError,
    LLMUnavailableError,
)
from valyra.ai.schemas import ExplainRequest, ExplainResponse
from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.errors import AppError, ErrorResponse

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
SessionDep = Annotated[Session, Depends(get_session)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]


@router.post(
    "/explain",
    name="ai_explain",
    response_model=ExplainResponse,
    summary="Explicar evidências da conta",
    description=(
        "O servidor autoriza a conta do usuário demo e monta o contexto corrente. "
        "Sem evidências elegíveis, retorna insuficiência sem chamar o provedor. "
        "Não persiste conversa, não faz replay histórico nem calcula resumo/projeção."
    ),
    responses={
        404: {
            "model": ErrorResponse,
            "description": "ACCOUNT_NOT_FOUND: conta inexistente ou alheia",
        },
        422: {"model": ErrorResponse, "description": "VALIDATION_ERROR: corpo inválido"},
        500: {
            "model": ErrorResponse,
            "description": "AI_CONFIGURATION_ERROR ou AI_CONTEXT_INVALID: falha de preparação",
        },
        502: {
            "model": ErrorResponse,
            "description": "AI_INVALID_RESPONSE: saída inválida ou rejeitada pelo domínio",
        },
        503: {
            "model": ErrorResponse,
            "description": "AI_UNAVAILABLE: provedor sem chave, cota ou acesso",
        },
    },
)
def explain(body: ExplainRequest, session: SessionDep, user_id: UserIdDep) -> ExplainResponse:
    # Sessão e SDK bloqueantes: FastAPI executa esta rota síncrona no threadpool.
    try:
        return service.explain_for_account(session, user_id, body)
    except LLMUnavailableError:
        raise AppError("AI_UNAVAILABLE", "Explicação indisponível no momento", 503) from None
    except LLMConfigurationError:
        raise AppError(
            "AI_CONFIGURATION_ERROR", "Falha na configuração da explicação", 500
        ) from None
    except (EvidenceContextError, LLMPromptError, ValidationError):
        raise AppError(
            "AI_CONTEXT_INVALID", "Não foi possível preparar a explicação", 500
        ) from None
    except (LLMParseError, ExplanationValidationError):
        # Não expor resposta bruta, IDs inventados, chaves ou exceções de validadores.
        raise AppError(
            "AI_INVALID_RESPONSE", "Não foi possível validar a explicação", 502
        ) from None
