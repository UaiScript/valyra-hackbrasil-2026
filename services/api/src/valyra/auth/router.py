
import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from valyra.auth.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from valyra.core.db import get_db, User
from valyra.core.config import settings
from valyra.models.password_reset_token import PasswordResetToken
from valyra.auth.emailSender import SMTPEmailService, EmailDeliveryError
from valyra.auth.service import get_password_hash


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def hash_token(token: str) -> str:
    """Calcula o SHA-256 do token de recuperação."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token() -> tuple[str, str]:
    """Gera token seguro e seu hash para persistência."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def is_valid_token(reset_token: PasswordResetToken) -> bool:
    now = datetime.now(timezone.utc)

    expires_at = reset_token.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return (
        reset_token.used_at is None
        and expires_at > now
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    generic_response = {
        "message": (
            "Se o e-mail estiver cadastrado, "
            "você receberá instruções para redefinir sua senha."
        )
    }

    email = str(payload.email).strip().lower()

    result = await db.execute(
        select(User).where(func.lower(User.email) == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        return generic_response

    token, token_hash = create_reset_token()

    try:
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )

        db.add(reset_record)
        await db.commit()

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Não foi possível processar a solicitação.",
        )

    reset_url = (
        f"{settings.FRONTEND_URL}/reset-password"
        f"?token={token}"
    )

    try:
        email_service = SMTPEmailService()

        email_service.send_password_reset(
            recipient=email,
            reset_url=reset_url,
        )

    except EmailDeliveryError:
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash
            )
            .values(used_at=datetime.now(timezone.utc))
        )
        await db.commit()

    return generic_response


@router.get(
    "/reset-password/validate",
    status_code=status.HTTP_200_OK,
)
async def reset_password_validate(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(token)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
    )

    reset_record = result.scalar_one_or_none()

    if reset_record is None or not is_valid_token(reset_record):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de recuperação inválido ou expirado.",
        )

    return {
        "valid": True,
        "message": "Token válido.",
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(payload.token)

    try:
        result = await db.execute(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash
            )
            .with_for_update()
        )

        reset_record = result.scalar_one_or_none()

        if reset_record is None or not is_valid_token(reset_record):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link de recuperação inválido ou expirado.",
            )

        user_result = await db.execute(
            select(User).where(
                User.id == reset_record.user_id
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível redefinir a senha.",
            )

        user.password = get_password_hash(payload.new_password)

        reset_record.used_at = datetime.now(timezone.utc)

        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.id != reset_record.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

        await db.commit()

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível redefinir a senha.",
        )

    return {
        "message": "Senha redefinida com sucesso."
    }
