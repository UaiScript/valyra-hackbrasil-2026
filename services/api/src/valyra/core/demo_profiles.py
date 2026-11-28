"""Clientes fictícios dos perfis da demonstração (apps/web/src/app/profiles.ts).

Cada perfil da demo é um usuário sintético próprio, com conta, histórico e orçamento
separados do usuário demo padrão. Assim a Central de cada perfil mostra números calculados
pelo Finance sobre um histórico coerente com a persona, em vez de reaproveitar a mesma conta.
Não é autenticação: qualquer visitante da demo pode escolher qualquer perfil.
"""

from uuid import UUID

# Os ids batem com os de profiles.ts; trocar uma persona no front exige trocar a chave aqui
# e os dados em valyra.scripts.seed_demo_profiles. UUIDs fixos tornam o seed idempotente.
DEMO_PROFILE_USERS: dict[str, UUID] = {
    "orcamento-apertado": UUID("00000000-0000-0000-0000-000000000011"),
    "comecando-a-investir": UUID("00000000-0000-0000-0000-000000000012"),
    "investidor": UUID("00000000-0000-0000-0000-000000000013"),
}

# Cabeçalho que o front envia com o perfil escolhido; sem ele vale o usuário demo padrão.
PROFILE_HEADER = "X-Valyra-Profile"
