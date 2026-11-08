"""Seed inicial; run não faz commit da transação do chamador."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from valyra.core.config import get_settings
from valyra.core.db import User, get_session_factory
from valyra.finance.models import Account, Category

DEMO_ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000101")
CATEGORIES = (
    ("mercado", "Mercado", "expense"),
    ("restaurantes", "Restaurantes", "expense"),
    ("transporte", "Transporte", "expense"),
    ("moradia", "Moradia", "expense"),
    ("contas-e-servicos", "Contas e serviços", "expense"),
    ("saude", "Saúde", "expense"),
    ("educacao", "Educação", "expense"),
    ("lazer", "Lazer", "expense"),
    ("assinaturas", "Assinaturas", "expense"),
    ("outros", "Outros", "expense"),
    ("salario", "Salário", "income"),
    ("outras-receitas", "Outras receitas", "income"),
)


class SeedConflictError(RuntimeError):
    """Dado existente incompatível que o seed não pode sobrescrever."""


def run(session: Session) -> None:
    """Insere faltantes por ID/slug; o chamador controla commit e rollback externos.

    O SAVEPOINT desfaz todas as inserções deste seed se houver conflito, mesmo se
    o chamador capturar a exceção e continuar a própria transação.
    """
    demo_id = get_settings().demo_user_id
    with session.begin_nested():
        session.execute(
            insert(User)
            .values(id=demo_id, name="Usuário demo")
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        session.execute(
            insert(Account)
            .values(
                id=DEMO_ACCOUNT_ID,
                user_id=demo_id,
                name="Conta principal",
                balance_cents=500000,
                balance_as_of=date(2026, 11, 1),
            )
            .on_conflict_do_nothing(index_elements=[Account.id])
        )
        owner = session.scalar(
            select(Account.user_id).where(Account.id == DEMO_ACCOUNT_ID).with_for_update()
        )
        if owner != demo_id:
            raise SeedConflictError(
                f"Conta fixa {DEMO_ACCOUNT_ID} pertence a outro usuário; "
                "nenhum dado foi reatribuído"
            )

        for slug, name, kind in CATEGORIES:
            session.execute(
                insert(Category)
                .values(slug=slug, name=name, kind=kind)
                .on_conflict_do_nothing(index_elements=[Category.slug])
            )
            # A chave natural mantém o UUID e o nome de categorias já existentes.
            existing_kind = session.scalar(
                select(Category.kind).where(Category.slug == slug).with_for_update()
            )
            if existing_kind != kind:
                raise SeedConflictError(
                    f"Categoria '{slug}' tem kind '{existing_kind}'; esperado '{kind}'"
                )


def main() -> None:
    try:
        # O contexto confirma tudo em sucesso ou desfaz tudo em qualquer exceção.
        with get_session_factory().begin() as session:
            run(session)
    except SeedConflictError as exc:
        raise SystemExit(f"Seed cancelado: {exc}") from exc


if __name__ == "__main__":
    main()
