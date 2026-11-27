import type { FC } from 'react';
import { BrainCircuit, ChartNoAxesCombined, Compass } from 'lucide-react';
import { pt } from '../content/pt';

/*
 * Os três módulos da Valyra com nome e subtítulo lidos da própria landing (content/pt.ts):
 * o app nunca diverge do que a página pública promete.
 */
export type ModuleId = 'finance' | 'alpha' | 'ai';

const [finance, alpha, ai] = pt.capabilities.items;

export const MODULES: Record<ModuleId, { title: string; subtitle: string; Icon: typeof Compass }> = {
  finance: { title: finance.title, subtitle: finance.subtitle, Icon: ChartNoAxesCombined },
  alpha: { title: alpha.title, subtitle: alpha.subtitle, Icon: Compass },
  ai: { title: ai.title, subtitle: ai.subtitle, Icon: BrainCircuit },
};

/** Selo do módulo: ícone, nome em destaque e subtítulo. */
export const ModuleBadge: FC<{ id: ModuleId; compact?: boolean }> = ({ id, compact }) => {
  const { title, subtitle, Icon } = MODULES[id];
  return (
    <span className={`cx-module cx-module--${id}${compact ? ' cx-module--compact' : ''}`}>
      <span className="cx-module__icon" aria-hidden="true"><Icon size={compact ? 13 : 15} /></span>
      <b>{title}</b>
      {!compact && <small>{subtitle}</small>}
    </span>
  );
};
