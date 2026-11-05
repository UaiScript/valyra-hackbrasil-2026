# Valyra

**Entenda os sinais. Decida com clareza.**

Demonstração de organização financeira e planejamento para pessoas e empresas, conectada à proposta de contexto econômico e IA explicável. Esta versão entrega landing, Visão geral, Financeiro, Planejamento e Radar com **dados sintéticos**.

## Começar

Requisitos: Node.js `>=22.12.0` e npm `>=10`, conforme `package.json`. Os checks completos também usam Python; a versão verificada foi 3.13.15, somente com a biblioteca padrão.

Na raiz:

```sh
npm ci
npm run dev
```

Abra a URL indicada pelo Vite, normalmente `http://127.0.0.1:5173`:

- Landing: `/#/`
- Demonstração Pessoal: `/#/demo/overview?profile=personal`
- Demonstração Empresa: `/#/demo/overview?profile=business`

Se a porta estiver ocupada, use a alternativa informada no terminal. Para conferir a entrega:

```sh
npm run check
npm run format:check
```

`check` executa tipos, testes, validação Python e build. A prévia compilada usa `npm run build` seguido de `npm run preview`.

## Continuar o projeto

- **Equipe:** [docs/README.md](docs/README.md) indica o que ler para cada tarefa.
- **Execução e ambiente:** [docs/desenvolvimento.md](docs/desenvolvimento.md).
- **Regras e limites:** [docs/regras-de-negocio.md](docs/regras-de-negocio.md).
- **Estado e verificações atuais:** [docs/estado-atual.md](docs/estado-atual.md).
- **Agentes de IA:** leia [AGENTS.md](AGENTS.md) e siga o mapa seletivo de `docs/README.md`.
- **Contribuição:** [CONTRIBUTING.md](CONTRIBUTING.md).

O código web fica em `apps/web/src/`; os dados, em `apps/web/src/data/demo/`; scripts auxiliares, em `scripts/`. A documentação técnica reutiliza [arquitetura-inicial.md](docs/arquitetura-inicial.md), sem uma segunda arquitetura concorrente.

## Limites desta versão

Não há login, persistência, conexão bancária, dados financeiros reais, notícias em tempo real ou IA conectada. O planejamento subtrai compromissos; o Radar apresenta exemplos editoriais e não altera os registros. A revisão visual em navegador real permanece pendente, assim como publicação HTTPS e atividades externas do evento.

Projeto em equipe para o Hack Brasil 2026: [UaiScript/valyra-hackbrasil-2026](https://github.com/UaiScript/valyra-hackbrasil-2026). O nome público é Valyra; `valyre` e `@valyre/web` são identificadores técnicos preservados. Próximas etapas estão no [escopo do MVP](docs/escopo-mvp.md).
