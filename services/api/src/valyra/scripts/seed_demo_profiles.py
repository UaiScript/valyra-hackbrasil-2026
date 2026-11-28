"""Semeia os clientes fictícios dos perfis da demonstração com alguns meses de extrato.

Uso: python -m valyra.scripts.seed_demo_profiles [--reset]

Cada perfil de apps/web/src/app/profiles.ts vira um usuário sintético com conta, orçamento
e um extrato de quatro meses (três fechados e o atual até "hoje"). O extrato entra pela
mesma importação CSV da tela Importar: categorias, recorrência, gastos atípicos e alertas
de pressão de caixa são calculados pelo Finance, não escritos à mão aqui.

Regras de segurança:
- Só toca nos usuários de core.demo_profiles; o usuário demo padrão e qualquer dado real
  ficam fora, inclusive no --reset.
- Sem --reset é idempotente: conta que já tem movimentação não recebe outro extrato, então
  alterações feitas durante a demo (categoria corrigida, orçamento editado) sobrevivem a um
  novo deploy.
- Datas relativas a core.clock.get_today(): com DEMO_TODAY fixo, o histórico não envelhece.

Todos os nomes, valores e descrições são sintéticos.
"""

import argparse
import calendar
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from valyra.alerts.models import Alert
from valyra.core import clock
from valyra.core.config import get_settings
from valyra.core.db import User, get_session_factory
from valyra.core.demo_profiles import DEMO_PROFILE_USERS
from valyra.finance import service as finance_service
from valyra.finance.models import Account, Budget, Category, ImportBatch, Transaction

# Meses fechados antes do atual: três dão à recorrência as 3 ocorrências mínimas (ADR-0010)
# e à média de gastos variáveis da projeção a janela inteira de 90 dias.
HISTORY_MONTHS = 3


@dataclass(frozen=True)
class Fixed:
    """Conta fixa mensal. `amounts` tem um valor por mês, do mais antigo ao atual."""

    day: int
    description: str
    amounts: tuple[int, ...]


@dataclass(frozen=True)
class Variable:
    """Gasto do dia a dia: `per_month` lançamentos com valor entre `low` e `high` centavos."""

    descriptions: tuple[str, ...]
    per_month: int
    low: int
    high: int


@dataclass(frozen=True)
class OneOff:
    """Lançamento avulso. `month` conta a partir do atual: 0 é este mês, -1 o anterior."""

    month: int
    day: int
    description: str
    amount: int


@dataclass(frozen=True)
class DemoProfile:
    key: str
    user_name: str
    account_id: UUID
    account_name: str
    # Saldo realizado desejado em "hoje"; o saldo de referência é derivado dele.
    balance_today: int
    fixed: tuple[Fixed, ...]
    variable: tuple[Variable, ...]
    one_offs: tuple[OneOff, ...]
    budgets: dict[str, int] = field(default_factory=dict)


def _months(value: int) -> tuple[int, ...]:
    return (value,) * (HISTORY_MONTHS + 1)


# Camila: salário curto, contas fixas pesadas e um mês atual que aperta. Os gastos de
# novembro acima do padrão fazem o saldo previsto ficar negativo antes do próximo salário.
CAMILA = DemoProfile(
    key="orcamento-apertado",
    user_name="Camila (perfil demo)",
    account_id=UUID("00000000-0000-0000-0000-000000000111"),
    account_name="Conta salário",
    balance_today=26_480,
    fixed=(
        Fixed(5, "Salario Loja Horizonte", _months(340_000)),
        Fixed(6, "Aluguel Kitnet Santa Efigenia", _months(-115_000)),
        Fixed(8, "Faculdade Mensalidade", _months(-38_900)),
        Fixed(10, "Cemig Energia", (-11_840, -12_410, -11_530, -12_960)),
        Fixed(12, "Internet Fibra Casa", _months(-9_990)),
        Fixed(15, "Spotify", _months(-2_190)),
        Fixed(18, "Netflix", _months(-4_490)),
        Fixed(20, "Telefone Celular Plano", _months(-5_990)),
    ),
    variable=(
        Variable(
            ("Supermercado Bom Preco", "Atacadao Contagem", "Hortifruti Savassi"), 6, 5_800, 13_900
        ),
        Variable(
            ("Ifood *Pedido", "Restaurante Sabor de Minas", "Padaria Pao Dourado"), 7, 1_800, 6_200
        ),
        Variable(("Uber *Trip", "99 corrida"), 8, 1_200, 3_400),
        Variable(("Drogaria Sao Lucas", "Farmacia Popular"), 2, 1_900, 5_200),
        Variable(("Cinema Shopping",), 1, 3_200, 5_600),
    ),
    one_offs=(
        OneOff(-2, 14, "Presente aniversario mae", -12_000),
        OneOff(-1, 22, "Conserto celular", -18_000),
        # Mês atual: o aperto que a Central precisa mostrar.
        OneOff(0, 9, "Drogaria Sao Lucas tratamento", -18_640),
        OneOff(0, 16, "Ingresso show Mineirao", -16_000),
        OneOff(0, 23, "Restaurante Sabor de Minas", -11_450),
    ),
    budgets={
        "mercado": 75_000,
        "restaurantes": 30_000,
        "transporte": 26_000,
        "contas-e-servicos": 32_000,
        "saude": 9_000,
        "lazer": 12_000,
        "assinaturas": 7_500,
    },
)

# Começando a investir: renda folgada, aplicação mensal no CDB e primeiras compras de ações.
# Sobra dinheiro todo mês; o destaque é um jantar fora do padrão e o orçamento de lazer.
INVESTIDOR = DemoProfile(
    key="comecando-a-investir",
    user_name="Começando a investir (perfil demo)",
    account_id=UUID("00000000-0000-0000-0000-000000000112"),
    account_name="Conta corrente",
    balance_today=684_350,
    fixed=(
        Fixed(5, "Salario Datacorp Analytics", _months(920_000)),
        Fixed(6, "Aplicacao CDB Liquidez Diaria", _months(-200_000)),
        Fixed(7, "Aluguel Apartamento Pinheiros", _months(-230_000)),
        Fixed(7, "Condominio Edificio Aurora", _months(-48_000)),
        Fixed(11, "Energia Eletrica", (-17_420, -18_930, -16_880, -18_150)),
        Fixed(12, "Internet Fibra 500 Mega", _months(-11_990)),
        Fixed(16, "Spotify", _months(-3_490)),
        Fixed(19, "Disney Plus", _months(-4_390)),
        Fixed(22, "Academia Movimento", _months(-12_990)),
    ),
    variable=(
        Variable(("Supermercado Pao de Mel", "Hortifruti Vila Madalena"), 5, 9_500, 24_000),
        Variable(
            ("Ifood *Pedido", "Restaurante Bistro Paulista", "Padaria Real"), 6, 3_200, 11_800
        ),
        Variable(("Uber *Trip", "99 corrida"), 6, 1_800, 4_900),
        Variable(("Cinema Paulista", "Ingresso teatro"), 2, 4_000, 9_000),
        Variable(("Livraria Cultura e Arte",), 1, 4_500, 12_000),
    ),
    one_offs=(
        OneOff(-3, 18, "Rendimento CDB", 1_820),
        OneOff(-2, 18, "Rendimento CDB", 3_140),
        OneOff(-1, 18, "Rendimento CDB", 4_470),
        OneOff(0, 18, "Rendimento CDB", 5_930),
        OneOff(-2, 9, "Compra acoes corretora", -80_000),
        OneOff(-1, 13, "Curso online investimentos", -29_700),
        OneOff(0, 10, "Compra acoes corretora", -120_000),
        OneOff(0, 14, "Dividendos acoes", 2_380),
        OneOff(0, 20, "Restaurante jantar aniversario", -54_000),
    ),
    budgets={
        "mercado": 100_000,
        "restaurantes": 60_000,
        "transporte": 30_000,
        "lazer": 25_000,
        "assinaturas": 10_000,
    },
)

# Investidor: renda alta, aportes mensais em fundo e Tesouro, carteira de ações e FIIs que
# já paga proventos todo mês. O destaque é uma compra grande de ações e um gasto fora do padrão.
INVESTIDOR_AVANCADO = DemoProfile(
    key="investidor",
    user_name="Investidor (perfil demo)",
    account_id=UUID("00000000-0000-0000-0000-000000000113"),
    account_name="Conta investimentos",
    balance_today=2_418_760,
    fixed=(
        Fixed(5, "Pro-labore Consultoria Prisma", _months(1_850_000)),
        Fixed(6, "Aplicacao fundo multimercado", _months(-500_000)),
        Fixed(6, "Aporte Tesouro IPCA", _months(-300_000)),
        Fixed(8, "Condominio Residencial Mirante", _months(-112_000)),
        Fixed(9, "Escola Bilingue mensalidade", _months(-298_000)),
        Fixed(10, "Plano de saude Vida Plena", _months(-148_900)),
        Fixed(14, "Rendimentos FII carteira", (126_430, 131_870, 129_150, 134_620)),
        Fixed(11, "Energia Eletrica", (-38_420, -41_760, -36_980, -40_310)),
        Fixed(13, "Internet Fibra 1 Giga", _months(-19_990)),
        Fixed(17, "Netflix", _months(-5_990)),
        Fixed(21, "Spotify", _months(-3_490)),
    ),
    variable=(
        Variable(("Supermercado Pao de Mel", "Hortifruti Gourmet"), 6, 22_000, 52_000),
        Variable(
            ("Restaurante Bistro Paulista", "Ifood *Pedido", "Padaria Real"), 7, 6_500, 24_000
        ),
        Variable(("Uber *Trip", "Posto Avenida combustivel"), 6, 4_500, 28_000),
        Variable(("Cinema Paulista", "Ingresso teatro"), 2, 9_000, 18_000),
        Variable(("Drogaria Bem Estar",), 2, 4_800, 16_000),
    ),
    one_offs=(
        OneOff(-3, 15, "Dividendos acoes", 48_210),
        OneOff(-2, 15, "Dividendos acoes", 21_930),
        OneOff(-1, 15, "Juros sobre capital proprio", 36_470),
        OneOff(0, 15, "Dividendos acoes", 62_880),
        OneOff(-3, 20, "Compra acoes corretora", -600_000),
        OneOff(-1, 7, "Compra ETF internacional", -450_000),
        OneOff(-2, 27, "Resgate CDB vencido", 1_200_000),
        OneOff(0, 12, "Compra acoes corretora", -1_500_000),
        OneOff(0, 18, "Ingresso show internacional", -186_000),
    ),
    budgets={
        "mercado": 280_000,
        "restaurantes": 150_000,
        "transporte": 120_000,
        "lazer": 60_000,
        "saude": 25_000,
    },
)

PROFILES: tuple[DemoProfile, ...] = (CAMILA, INVESTIDOR, INVESTIDOR_AVANCADO)


@dataclass(frozen=True)
class Row:
    date: date
    description: str
    amount: int


def _month_start(today: date, offset: int) -> date:
    index = today.year * 12 + today.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def _on(month: date, day: int) -> date:
    return month.replace(day=min(day, calendar.monthrange(month.year, month.month)[1]))


def build_rows(profile: DemoProfile, today: date) -> list[Row]:
    """Extrato do perfil até `today`, sempre igual para o mesmo perfil e a mesma data."""
    # Semente fixa por perfil: o mesmo deploy gera o mesmo extrato (e o mesmo hash de linha).
    rng = random.Random(f"valyra-demo:{profile.key}")
    rows: list[Row] = []
    for index, offset in enumerate(range(-HISTORY_MONTHS, 1)):
        month = _month_start(today, offset)
        last_day = calendar.monthrange(month.year, month.month)[1]
        # No mês atual só existe o que já aconteceu; o resto do mês é papel da projeção.
        visible_days = today.day if offset == 0 else last_day
        for item in profile.fixed:
            rows.append(Row(_on(month, item.day), item.description, item.amounts[index]))
        for item in profile.variable:
            # Proporcional aos dias já vividos, para o mês atual não parecer cheio demais.
            count = round(item.per_month * visible_days / last_day)
            for _ in range(count):
                day = rng.randint(1, visible_days)
                amount = rng.randint(item.low, item.high)
                rows.append(Row(_on(month, day), rng.choice(item.descriptions), -amount))
        for one_off in profile.one_offs:
            if one_off.month == offset:
                rows.append(Row(_on(month, one_off.day), one_off.description, one_off.amount))
    return sorted((r for r in rows if r.date <= today), key=lambda r: (r.date, r.description))


def _reais(cents: int) -> str:
    # Formata sem float: o CSV aceita no máximo duas casas e a conversão precisa ser exata.
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"


def to_csv(rows: Iterable[Row]) -> bytes:
    lines = ["date,description,amount"]
    lines += [f"{r.date.isoformat()},{r.description},{_reais(r.amount)}" for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _ensure_owner_and_budgets(session: Session, profile: DemoProfile, user_id: UUID) -> None:
    session.execute(
        insert(User)
        .values(id=user_id, name=profile.user_name)
        .on_conflict_do_nothing(index_elements=[User.id])
    )
    session.execute(
        insert(Account)
        .values(
            id=profile.account_id,
            user_id=user_id,
            name=profile.account_name,
            balance_cents=0,
            balance_as_of=clock.get_today(),
        )
        .on_conflict_do_nothing(index_elements=[Account.id])
    )
    owner = session.scalar(select(Account.user_id).where(Account.id == profile.account_id))
    if owner != user_id:
        raise SystemExit(f"Conta {profile.account_id} pertence a outro usuário; nada foi alterado")
    # Categorias vêm do seed base (valyra.seed), que roda antes deste script.
    categories = {slug: cid for slug, cid in session.execute(select(Category.slug, Category.id))}
    for slug, limit_cents in profile.budgets.items():
        session.execute(
            insert(Budget)
            .values(user_id=user_id, category_id=categories[slug], limit_cents=limit_cents)
            .on_conflict_do_nothing(index_elements=[Budget.user_id, Budget.category_id])
        )


def _reset(session: Session, profile: DemoProfile, user_id: UUID) -> None:
    """Apaga extrato, lotes, alertas e orçamento do perfil; usuário e conta fixos ficam."""
    session.execute(delete(Alert).where(Alert.user_id == user_id))
    session.execute(delete(Transaction).where(Transaction.account_id == profile.account_id))
    # Rejeições de importação saem em cascata com o lote.
    session.execute(delete(ImportBatch).where(ImportBatch.account_id == profile.account_id))
    session.execute(delete(Budget).where(Budget.user_id == user_id))


def seed_profile(session: Session, profile: DemoProfile, *, reset: bool = False) -> bool:
    """Garante o perfil semeado; devolve True se importou um extrato novo."""
    user_id = DEMO_PROFILE_USERS[profile.key]
    if user_id == get_settings().demo_user_id:
        # Defesa extra: o usuário demo padrão recebe dados pela tela de importação, nunca daqui.
        raise SystemExit(f"Perfil {profile.key} aponta para o usuário demo padrão")
    if reset:
        _reset(session, profile, user_id)
    _ensure_owner_and_budgets(session, profile, user_id)
    if session.scalar(select(exists().where(Transaction.account_id == profile.account_id))):
        session.commit()
        return False

    today = clock.get_today()
    rows = build_rows(profile, today)
    # Fechamento no último dia do mês anterior, como um cliente que confere o saldo na virada
    # do mês: só o mês atual entra no saldo realizado, que termina exatamente em balance_today.
    # Os meses anteriores continuam servindo à recorrência, aos atípicos e à projeção.
    as_of = _month_start(today, 0) - timedelta(days=1)
    current_month = sum(r.amount for r in rows if r.date > as_of)
    session.execute(
        update(Account)
        .where(Account.id == profile.account_id)
        .values(balance_cents=profile.balance_today - current_month, balance_as_of=as_of)
    )
    session.flush()
    # Mesma porta de entrada da tela Importar; o service faz o commit da transação inteira.
    finance_service.import_csv(
        session,
        user_id,
        profile.account_id,
        f"extrato-{profile.key}-{today:%Y-%m}.csv",
        to_csv(rows),
    )
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reset",
        action="store_true",
        help="apaga e recria o histórico dos perfis fictícios (o usuário demo padrão não muda)",
    )
    args = parser.parse_args(argv)
    factory = get_session_factory()
    for profile in PROFILES:
        with factory() as session:
            imported = seed_profile(session, profile, reset=args.reset)
        print(f"{profile.key}: {'extrato importado' if imported else 'já semeado, mantido'}")


if __name__ == "__main__":
    main()
