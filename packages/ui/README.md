# Estilos compartilhados da Valyra

A base visual fica em `src/styles/`. `tokens.css` define valores primitivos,
`themes.css` define cores semânticas e temas, `typography.css` define tipografia
e `globals.css` reúne reset, layout e padrões de componentes.

Importe `src/styles/index.css` antes dos estilos específicos da aplicação.
Na landing, em `apps/landing/src/index.css`, use:

```css
@import "tailwindcss";
@import "../../../packages/ui/src/styles/index.css";
```

Os temas podem ser selecionados por `data-theme="light"` ou
`data-theme="dark"`, conforme os seletores de `themes.css`.
Prefira os tokens semânticos (`--color-*`) nos componentes e mantenha ajustes
específicos de cada página na própria aplicação.
