from datetime import datetime

class PasswordResetToken:
    """
    Representação conceitual do registro de recuperação.

    Campos necessários:
    """

    id: int
    user_id: int
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime