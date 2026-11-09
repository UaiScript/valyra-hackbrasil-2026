# Landing page do Valyra

Página estática de apresentação, adaptada do arquivo `valyra-intelligence.zip` fornecido pela equipe. Mantém o tema escuro, gráficos SVG, controles demonstrativos e idiomas PT/EN. A comunicação foi alinhada à proposta e ao estágio registrados no README principal.

`apps/landing` é um pacote independente. O futuro frontend da aplicação continua previsto em `apps/web`. Não existe integração com a API, PostgreSQL, feeds financeiros ou provedor de IA nesta landing. Os dados e os números exibidos são **sintéticos**, sem previsões ou resultados reais.

## Executar localmente

Requisitos: Node.js **22.12 ou superior** e npm. Validação local realizada com Node 24.19.0 e npm 11.17.0. Na raiz do repositório:

```sh
npm --prefix apps/landing ci --ignore-scripts
npm --prefix apps/landing run dev
```

Abra <http://127.0.0.1:3000>. Não é necessário criar `.env`, iniciar Docker ou configurar chaves de API. O servidor de desenvolvimento aceita conexões somente em loopback e exige a porta configurada livre.

```sh
npm --prefix apps/landing test
npm --prefix apps/landing run build
npm --prefix apps/landing run preview
```

O build executa a checagem TypeScript e gera `apps/landing/dist/`. O preview local usa <http://127.0.0.1:4173>; serve para conferir o build, não para hospedar produção.

## Navegador e CI

Na pasta `apps/landing`:

```sh
npx --no-install playwright install chromium
npm run build
npm run test:e2e
npm audit --audit-level=moderate
```

O Playwright inicia e encerra seu próprio preview na porta 4173; pare um preview manual antes de rodar os testes. No Windows com Google Chrome já instalado, é possível evitar o download do Chromium:

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run test:e2e
Remove-Item Env:PLAYWRIGHT_CHANNEL
```

A suíte cobre desktop e celulares de 390 e 320 pixels: destino efetivo dos links, descarte de destino antigo no armazenamento, idioma persistente, funcionamento sem armazenamento, controles dos exemplos, ausência de requisições a terceiros, política de conteúdo e navegação por teclado. Há também testes de configuração para URLs inválidas e credenciais embutidas. Resultados e capturas ficam ignorados em `test-results/`.

O workflow separado [landing.yml](../../.github/workflows/landing.yml) executa instalação pelo lockfile, auditoria, testes de configuração, build e testes de navegador. Usa permissões somente de leitura e ações fixadas por SHA. Não publica o site nem modifica o CI do Finance. O resultado remoto deve ser acompanhado nos checks da branch/PR.

Validação local em **08/11/2026**: instalação pelo lockfile com scripts desabilitados, TypeScript/build aprovados, **10 testes de configuração e 18 testes de navegador aprovados**, sem testes ignorados. `npm audit` retornou zero vulnerabilidades conhecidas. Os builds também foram servidos em subpastas locais: destino padrão e modo futuro `application`, rótulos PT/EN e link alternativo sem JavaScript funcionaram; um destino com protocolo executável foi rejeitado pelo build. O endereço da aplicação usado nesse ensaio foi fictício, sem acesso externo. Os resultados remotos devem ser consultados nos checks do PR. Esta entrega não configura deploy público.

## Destino dos links de acesso

O padrão, sem arquivo local de configuração, é:

```text
https://github.com/UaiScript/valyra-hackbrasil-2026
```

Quando a aplicação oficial estiver estabelecida, crie **`apps/landing/.env.local`** a partir de `.env.example` desta pasta, defina a URL oficial e o tipo de destino:

```dotenv
VITE_SYSTEM_URL=https://app.seu-dominio-oficial.example
VITE_DESTINATION_KIND=application
```

O domínio acima é apenas ilustrativo. Substitua-o pelo domínio real e gere/publice um novo build. Reinicie também o servidor se estiver em desenvolvimento. A configuração é incorporada ao build, não editável pelo visitante. Os textos dos links de acesso acompanham o tipo de destino; o link institucional no rodapé e a alternativa sem JavaScript continuam apontando ao GitHub.

O build rejeita URL sem HTTPS, relativa, com protocolo executável ou credenciais embutidas. No modo `repository`, aceita exclusivamente o repositório oficial. O modo `application` exige URL explícita. A validação do endereço não comprova a propriedade de um domínio: a equipe deve configurar seu endereço oficial.

Não use o `.env` do backend. Todo valor `VITE_*` deve ser tratado como **público**, nunca como segredo. O `.env.local` é ignorado pelo Git. A configuração Vite carrega o ambiente desta pasta e não importa as variáveis do Finance.

## Organização e segurança

```text
apps/landing/
├── config/destination.mjs   # validação do destino durante o build
├── public/                 # favicon local
├── src/
│   ├── components/         # seções independentes da página
│   ├── content/            # textos PT/EN e rótulos do destino
│   ├── data/demo.ts        # séries e cenários sintéticos
│   ├── types/             # contratos da apresentação
│   ├── App.tsx            # composição e preferência de idioma
│   └── index.css
├── tests/                  # configuração e navegação real em navegador
├── package-lock.json       # dependências reproduzíveis
└── vite.config.mjs
```

Foram excluídos os planos, metadados e ativos não utilizados do AI Studio; SDK de IA, servidor Express, dotenv e outras dependências sem uso também não foram importados. O aviso SPDX Apache-2.0 presente no `App.tsx` de origem foi preservado no arquivo adaptado; isso não define a licença dos demais componentes do monorepo.

Não há formulários, analytics, chamadas de API, fontes remotas ou imagens de terceiros. Apenas a preferência de idioma é salva no navegador, quando disponível. Links de saída são âncoras comuns, sem modal de URL ou redirecionamento automático. A página permanece navegável quando o armazenamento local está bloqueado; sem JavaScript, apresenta um link ao repositório.

O HTML de produção inclui CSP com scripts locais, conexões de rede desabilitadas e formulários proibidos. Estilos inline são permitidos para as dimensões dos gráficos SVG; scripts inline não são permitidos. Dependências não executam scripts de instalação no fluxo documentado. `node_modules`, `dist`, logs e resultados dos testes ficam ignorados pelo Git.

## Hospedagem e remoção

Publique apenas o conteúdo de `dist/` em um host estático HTTPS; nunca o diretório do repositório, `.env`, fontes locais de ferramentas ou `node_modules`. A base relativa `./` permite hospedar o build em uma subpasta, inclusive no caminho de um projeto no GitHub Pages. Veja o [guia oficial de deploy do Vite](https://vite.dev/guide/static-deploy). Nenhum workflow de deploy automático ou domínio foi configurado nesta entrega.

No host de produção, configure também os headers HTTP `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` e uma CSP com `frame-ancestors 'none'` (essa diretiva requer header HTTP). Se a hospedagem não permitir headers personalizados, a CSP no HTML continua restringindo scripts e conexões, mas não impede incorporação da página em frames.

Para remover a landing, remova somente `apps/landing/`, `.github/workflows/landing.yml` e a seção **Landing page** do README principal. Caso tenha sido hospedada, desative essa publicação separadamente. Não há pacote compartilhado, serviço Compose, migração ou alteração de backend para reverter.
