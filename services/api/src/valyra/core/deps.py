"""Identidade demo; não implementa autenticação ou isolamento por sessão."""

from typing import Annotated
from uuid import UUID

from fastapi import Header

from valyra.core.config import get_settings
from valyra.core.demo_profiles import DEMO_PROFILE_USERS, PROFILE_HEADER


def get_current_user_id(
    # Fora do OpenAPI: é um seletor da demonstração, não um contrato para clientes reais.
    profile: Annotated[str | None, Header(alias=PROFILE_HEADER, include_in_schema=False)] = None,
) -> UUID:
    # Perfil desconhecido cai no usuário demo padrão, como se o cabeçalho não existisse:
    # um front com perfil renomeado continua funcionando, só sem o histórico do perfil.
    if profile is not None and profile in DEMO_PROFILE_USERS:
        return DEMO_PROFILE_USERS[profile]
    return get_settings().demo_user_id
