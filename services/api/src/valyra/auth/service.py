import hashlib
import secrets


def generate_reset_token() -> tuple[str, str]:
    """
    Retorna o token original e seu hash.

    O original será enviado por e-mail.
    Apenas o hash será armazenado no banco.
    """

    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    return token, token_hash


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()