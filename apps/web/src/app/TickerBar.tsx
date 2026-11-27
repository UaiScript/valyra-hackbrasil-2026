import { useMemo } from 'react';
import type { FC } from 'react';
import { CandlestickChart, CloudSun, Newspaper } from 'lucide-react';
import { api } from './api/client';
import type { RadarOut, WeeklyNewsOut } from '../lib/api/schema';
import { compareDecimal, formatDecimal, formatShortDate } from './money';
import type { TickerMode } from './profiles';
import { TICKER_MODES } from './profiles';
import { useApi } from './useApi';
import { useProfile } from './useProfile';

/*
 * Faixa do topo da Central, personalizável: bolsa (brapi + juros do Banco Central),
 * manchetes (relatório da semana) ou clima nas regiões produtoras (Open-Meteo). Os
 * valores são o texto que a fonte publicou, sem conversão para float, e cada modo cita
 * a fonte no fim da faixa. Só o modo ativo é buscado na API.
 */

type Tone = 'up' | 'down' | 'flat' | 'dry' | 'wet';
type Item = { key: string; label: string; value: string; note?: string; tone: Tone; href?: string };

const MODE_META: Record<TickerMode, { label: string; Icon: typeof Newspaper; aria: string }> = {
  bolsa: { label: 'Bolsa', Icon: CandlestickChart, aria: 'Bolsa e juros: variação do dia das ações do radar, Selic, CDI e IPCA' },
  manchetes: { label: 'Manchetes', Icon: Newspaper, aria: 'Manchetes da semana sobre economia' },
  clima: { label: 'Clima', Icon: CloudSun, aria: 'Chuva nas regiões produtoras contra a média de 10 anos' },
};

function signTone(value: string): Tone {
  const c = compareDecimal(value, '0');
  return c > 0 ? 'up' : c < 0 ? 'down' : 'flat';
}
const arrow = (t: Tone) => (t === 'up' ? '▲' : t === 'down' ? '▼' : '■');

export function stockItems(r: RadarOut): Item[] {
  const stocks = r.indicators.filter((i) => i.theme === 'acoes').map((i): Item => {
    const t = signTone(i.latest.value);
    return { key: i.key, label: i.title.split(':')[0], value: `${arrow(t)} ${formatDecimal(i.latest.value)}%`,
      // Data da cotação sempre visível: em fim de semana, feriado ou coleta parada, o
      // último pregão pode ser de dias atrás, e "no dia" sozinho afirmaria uma recência falsa.
      note: `pregão de ${formatShortDate(i.latest.observation_date)}`, tone: t };
  });
  const macro = r.indicators.filter((i) => i.theme === 'juros' || i.theme === 'inflacao').map((i): Item => ({
    key: i.key, label: i.title.toUpperCase(), value: formatDecimal(i.latest.value), note: `${i.unit_label} · ${formatShortDate(i.latest.observation_date)}`, tone: 'flat',
  }));
  return [...stocks, ...macro];
}

export function climateItems(r: RadarOut): Item[] {
  const rains = r.indicators.filter((i) => i.theme === 'clima' && i.unit === 'mm');
  return rains.map((rain): Item => {
    // Sem região não há como parear com segurança: mostra só os milímetros.
    const slug = rain.region?.slug;
    const anomaly = slug ? r.indicators.find((i) => i.theme === 'clima' && i.unit === '%' && i.region?.slug === slug) : undefined;
    const until = `até ${formatShortDate(rain.latest.observation_date)}`;
    const c = anomaly ? compareDecimal(anomaly.latest.value, '0') : 0;
    return {
      key: rain.key,
      label: (rain.region?.name ?? rain.title).toUpperCase(),
      value: `${formatDecimal(rain.latest.value)} mm`,
      note: anomaly ? `${c < 0 ? '▼' : c > 0 ? '▲' : '■'} ${formatDecimal(anomaly.latest.value.replace('-', ''))}% ${c < 0 ? 'abaixo' : 'acima'} da média · ${until}` : `em 30 dias · ${until}`,
      tone: c < 0 ? 'dry' : c > 0 ? 'wet' : 'flat',
    };
  });
}

export function headlineItems(w: WeeklyNewsOut, max = 12): Item[] {
  const seen = new Set<string>();
  return w.themes
    .flatMap((t) => t.items)
    .filter((n) => (seen.has(n.signal_key) ? false : (seen.add(n.signal_key), true)))
    .sort((a, b) => (a.published_at < b.published_at ? 1 : a.published_at > b.published_at ? -1 : 0))
    .slice(0, max)
    .map((n): Item => ({ key: n.signal_key, label: shortSource(n.source.name), value: n.title, tone: 'flat', href: n.url }));
}

/** "Agência Brasil (EBC) — Economia" → "AGÊNCIA BRASIL": a faixa só tem espaço para o nome. */
function shortSource(name: string): string {
  return name.split(/ — | \(/)[0].toUpperCase();
}

const SOURCE_NOTE: Record<TickerMode, string> = {
  bolsa: 'brapi.dev, cotação com atraso · Banco Central (SGS)',
  manchetes: 'Título e link para a matéria original',
  clima: 'Open-Meteo (CC BY 4.0) · chuva observada em 30 dias',
};
const EMPTY_NOTE: Record<TickerMode, string> = {
  bolsa: 'Sem cotações coletadas até agora. A coleta roda de hora em hora no pregão.',
  manchetes: 'Sem manchetes coletadas nos últimos 7 dias.',
  clima: 'Sem dados de chuva coletados até agora. A coleta roda uma vez por dia.',
};

const ModeSwitch: FC<{ mode: TickerMode; onChange: (m: TickerMode) => void }> = ({ mode, onChange }) => (
  <div className="cx-ticker__modes" role="group" aria-label="O que a faixa mostra">
    {TICKER_MODES.map((m) => {
      const { label, Icon } = MODE_META[m];
      return (
        <button key={m} type="button" className="cx-ticker__mode" aria-pressed={m === mode} title={label} onClick={() => onChange(m)}>
          <Icon size={14} aria-hidden="true" /><span>{label}</span>
        </button>
      );
    })}
  </div>
);

const Track: FC<{ items: Item[]; mode: TickerMode }> = ({ items, mode }) => {
  const row = (copy: boolean) => (
    <div className="cx-ticker__row" aria-hidden={copy || undefined}>
      {items.map((it) => {
        const body = (
          <>
            <b>{it.label}</b><span className="cx-ticker__value">{it.value}</span>
            {it.note && <em>{it.note}</em>}
          </>
        );
        const cls = `cx-ticker__item cx-ticker__item--${it.tone}`;
        // A cópia do laço não recebe foco: o teclado passa uma vez por manchete.
        return it.href
          ? <a key={it.key} className={cls} href={it.href} target="_blank" rel="noreferrer" tabIndex={copy ? -1 : undefined}>{body}</a>
          : <span key={it.key} className={cls}>{body}</span>;
      })}
      <span className="cx-ticker__source">Fonte: {SOURCE_NOTE[mode]}</span>
    </div>
  );
  // Poucos itens não enchem a faixa: o laço fica curto e a velocidade acompanha o tamanho.
  const seconds = Math.max(28, items.length * (mode === 'manchetes' ? 9 : 5));
  return (
    <div className="cx-ticker__viewport">
      <div className="cx-ticker__track" style={{ animationDuration: `${seconds}s` }}>
        {row(false)}
        {row(true)}
      </div>
    </div>
  );
};

const Feed: FC<{ mode: TickerMode }> = ({ mode }) => {
  const radar = useApi((s) => (mode === 'manchetes' ? Promise.resolve(undefined) : api.getAlphaRadar(undefined, s)), [mode === 'manchetes']);
  const news = useApi((s) => (mode === 'manchetes' ? api.getWeeklyNews(undefined, s) : Promise.resolve(undefined)), [mode === 'manchetes']);
  const state = mode === 'manchetes' ? news.state : radar.state;
  const items = useMemo(() => {
    // Faixa decorativa: resposta parcial ou API antiga só esvazia a faixa, nunca derruba a Central.
    try {
      if (mode === 'manchetes') return news.state.data ? headlineItems(news.state.data) : null;
      if (!radar.state.data) return null;
      return mode === 'bolsa' ? stockItems(radar.state.data) : climateItems(radar.state.data);
    } catch {
      return [];
    }
  }, [mode, radar.state.data, news.state.data]);

  if (items === null) {
    return <div className="cx-ticker__viewport cx-ticker__viewport--static"><span className="cx-ticker__status">{state.status === 'error' ? 'Faixa indisponível agora; o radar volta na próxima checagem.' : 'Carregando…'}</span></div>;
  }
  if (items.length === 0) {
    return <div className="cx-ticker__viewport cx-ticker__viewport--static"><span className="cx-ticker__status">{EMPTY_NOTE[mode]}</span></div>;
  }
  return <Track key={mode} items={items} mode={mode} />;
};

export const TickerBar: FC = () => {
  const { ticker, setTicker } = useProfile();
  return (
    <section className={`cx-ticker cx-ticker--${ticker}`} aria-label={MODE_META[ticker].aria}>
      <ModeSwitch mode={ticker} onChange={setTicker} />
      <Feed mode={ticker} />
    </section>
  );
};
