"""Identidade demo; não implementa autenticação ou isolamento por sessão."""

from uuid import UUID

from valyra.core.config import get_settings


def get_current_user_id() -> UUID:
    return get_settings().demo_user_id
