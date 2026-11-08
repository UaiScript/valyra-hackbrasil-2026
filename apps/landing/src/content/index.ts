import { pt } from './pt';
import { en } from './en';
export { ALPHA_MODELS, COCKPIT_TIMEFRAMES, MACRO_SCENARIOS } from '../data/demo';

// Labels change along with the public destination, keeping the repository link in the footer.
if (__DESTINATION__.kind === 'application') {
  for (const [lang, t] of Object.entries({ pt, en })) {
    const isPt = lang === 'pt';
    t.nav.accessSystem = t.hero.ctaPrimary = t.ctaBanner.button = isPt ? 'Acessar aplicação' : 'Open application';
    t.cockpit.launchConsole = t.alternativeAlpha.terminalAction = isPt ? 'Conhecer a aplicação' : 'Explore the application';
    t.ctaBanner.title = isPt ? 'Conheça a aplicação oficial do Valyra' : 'Discover the official Valyra application';
    t.ctaBanner.description = isPt ? 'Continue para a aplicação oficial. Os gráficos desta landing permanecem demonstrativos.' : 'Continue to the official application. Charts on this landing page remain demonstrations.';
    t.ctaBanner.deploymentBadge = isPt ? 'APLICAÇÃO OFICIAL' : 'OFFICIAL APPLICATION';
    t.demoNotice = t.demoNotice.replace('Os links de acesso levam ao repositório oficial.', 'Os links de acesso levam à aplicação oficial.').replace('Access links lead to the official repository.', 'Access links lead to the official application.');
  }
}
export const CONTENT = { pt, en };
