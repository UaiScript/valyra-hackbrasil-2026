# ADR-0001 — Backend único modular no monorepo

## Contexto

Quatro desenvolvedores precisam entregar uma jornada financeira demonstrável no hackathon. O handoff v0.4 descrevia três serviços, mas o usuário definiu explicitamente a [fundação técnica](../spec-tecnica.md) como modelo arquitetural final.

## Decisão

Manter um monorepo com frontend React/TypeScript e **um backend FastAPI**, organizado por domínio. Separar router, schema, service, domínio e persistência; comunicação interna via services, sem HTTP entre módulos do mesmo processo.

Finance, Alpha e AI compõem a fundação. Alerts aparece como módulo interno no desenho posterior da modelagem; sua implementação e schema seguem os alinhamentos do respectivo incremento.

## Alternativas consideradas

- Três microsserviços: maior custo operacional e de coordenação para este prazo; não é o modelo final escolhido.
- Camadas globais sem domínios: dificulta ownership e manutenção em paralelo.
- Clean/Hexagonal completa por módulo: mais boilerplate do que a fundação exige neste momento.

## Consequências

Deploy e execução de aplicação ficam mais simples, mas é necessário preservar fronteiras internas por revisão e testes. O banco admite FKs entre módulos sem autorizar acoplamento de casos de uso. Extração futura de serviço exige nova ADR e contratos explícitos; não se faz silenciosamente.

## Status

**Aceita.** Escolha explícita do usuário na conciliação da arquitetura, registrada nesta entrega de contexto em 07/11/2026. Desenho aceito não comprova implementação.
