from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from valyra import seed
from valyra.core.config import Settings
from valyra.core.db import User
from valyra.finance.models import Account, Category

pytestmark = pytest.mark.postgres
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
EXPECTED = {
    "mercado": ("Mercado", "expense"),
    "restaurantes": ("Restaurantes", "expense"),
    "transporte": ("Transporte", "expense"),
    "moradia": ("Moradia", "expense"),
    "contas-e-servicos": ("Contas e serviços", "expense"),
    "saude": ("Saúde", "expense"),
    "educacao": ("Educação", "expense"),
    "lazer": ("Lazer", "expense"),
    "assinaturas": ("Assinaturas", "expense"),
    "outros": ("Outros", "expense"),
    "salario": ("Salário", "income"),
    "outras-receitas": ("Outras receitas", "income"),
}


@pytest.fixture(autouse=True)
def seed_settings(monkeypatch):
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/unused",
        demo_user_id=DEMO_USER_ID,
    )
    monkeypatch.setattr(seed, "get_settings", lambda: settings)


def test_seed_creates_expected_data(db_session):
    seed.run(db_session)
    assert db_session.get(User, DEMO_USER_ID).name == "Usuário demo"
    account = db_session.get(Account, UUID("00000000-0000-0000-0000-000000000101"))
    assert (account.name, account.user_id, account.balance_cents, account.balance_as_of) == (
        "Conta principal",
        DEMO_USER_ID,
        500000,
        date(2026, 11, 1),
    )
    actual = {c.slug: (c.name, c.kind) for c in db_session.scalars(select(Category))}
    assert actual == EXPECTED


def test_reexecution_preserves_ids_and_edits(db_session):
    seed.run(db_session)
    categories = {c.slug: c.id for c in db_session.scalars(select(Category))}
    user = db_session.get(User, DEMO_USER_ID)
    account = db_session.get(Account, seed.DEMO_ACCOUNT_ID)
    user.name = "Demo editado"
    account.name = "Conta editada"
    account.balance_cents = -421050
    account.balance_as_of = date(2026, 11, 7)
    db_session.get(Category, categories["salario"]).name = "Nome personalizado"
    db_session.flush()
    updated_at = account.updated_at
    seed.run(db_session)
    db_session.expire_all()
    assert {c.slug: c.id for c in db_session.scalars(select(Category))} == categories
    assert db_session.scalar(select(func.count()).select_from(Account)) == 1
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert user.name == "Demo editado"
    assert (account.name, account.balance_cents, account.balance_as_of, account.updated_at) == (
        "Conta editada",
        -421050,
        date(2026, 11, 7),
        updated_at,
    )
    assert db_session.get(Category, categories["salario"]).name == "Nome personalizado"


def test_existing_category_is_resolved_by_slug(db_session):
    existing_id = uuid4()
    db_session.add(Category(id=existing_id, slug="mercado", name="Meu mercado", kind="expense"))
    db_session.flush()
    seed.run(db_session)
    assert db_session.get(Category, existing_id).name == "Meu mercado"
    assert db_session.scalar(select(func.count()).select_from(Category)) == 12


def test_seed_does_not_commit_callers_transaction(db_session):
    seed.run(db_session)
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Account)) == 0
    assert db_session.scalar(select(func.count()).select_from(Category)) == 0


def test_account_conflict_rolls_back_seed_only(db_session):
    other = User(name="Outro usuário")
    db_session.add(other)
    db_session.flush()
    account = Account(
        id=seed.DEMO_ACCOUNT_ID,
        user_id=other.id,
        name="Preservada",
        balance_cents=123,
        balance_as_of=date(2026, 1, 1),
    )
    db_session.add(account)
    db_session.flush()
    with pytest.raises(seed.SeedConflictError, match="pertence a outro"):
        seed.run(db_session)
    # Capturar o conflito e confirmar o trabalho anterior não pode confirmar parte do seed.
    db_session.commit()
    assert db_session.get(User, DEMO_USER_ID) is None
    assert db_session.get(Account, seed.DEMO_ACCOUNT_ID).user_id == other.id
    assert db_session.get(Account, seed.DEMO_ACCOUNT_ID).balance_cents == 123
    assert db_session.scalar(select(func.count()).select_from(Category)) == 0


def test_late_category_conflict_leaves_no_partial_seed(db_session):
    # Último slug: o seed já tentou inserir usuário, conta e 11 categorias antes do conflito.
    existing = Category(slug="outras-receitas", name="Preservada", kind="expense")
    db_session.add(existing)
    db_session.flush()
    with pytest.raises(seed.SeedConflictError, match="outras-receitas"):
        seed.run(db_session)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Account)) == 0
    assert db_session.scalar(select(func.count()).select_from(Category)) == 1
    assert db_session.get(Category, existing.id).name == "Preservada"
