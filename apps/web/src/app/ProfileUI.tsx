import { useEffect, useRef, useState } from 'react';
import type { FC } from 'react';
import { ArrowUpRight, Check, ChevronDown, UserRoundCog } from 'lucide-react';
import { askHref } from './api/ai';
import { MODULES } from './modules';
import { PROFILES } from './profiles';
import type { Profile, ProfileShortcut, TickerMode } from './profiles';
import { ROUTES } from './router';
import { useProfile } from './useProfile';

/*
 * Peças de perfil: o seletor da Central (primeira visita ou "Trocar perfil"), a faixa
 * "Para você" com um atalho por módulo e o menu de perfil no cabeçalho. Tudo vem de
 * profiles.ts; aqui só há apresentação.
 */

const TICKER_LABEL: Record<TickerMode, string> = { bolsa: 'Bolsa', manchetes: 'Manchetes', clima: 'Clima' };

const shortcutHref = (s: ProfileShortcut) => (s.module === 'ai' ? askHref(s.question) : ROUTES[s.route]);

const ProfileCard: FC<{ p: Profile; active: boolean; onPick: () => void }> = ({ p, active, onPick }) => (
  <li>
    <button type="button" className="cx-profile-card" aria-pressed={active} onClick={onPick}>
      <span className="cx-profile-card__head">
        <span className="cx-profile-avatar" aria-hidden="true">{p.initial}</span>
        <span><b>{p.name}</b><small>{p.persona}</small></span>
        {active && <Check size={16} className="cx-profile-card__check" aria-hidden="true" />}
      </span>
      <span className="cx-profile-card__need">{p.need}</span>
      <span className="cx-profile-card__tags">
        <i>Foco: {MODULES[p.modules[0]].title}</i>
        <i>Faixa: {TICKER_LABEL[p.ticker]}</i>
      </span>
      <span className="cx-profile-card__plan">{p.plan}</span>
    </button>
  </li>
);

const Picker: FC<{ onDone?: () => void }> = ({ onDone }) => {
  const { profile, chosen, setProfile } = useProfile();
  return (
    <section className="cx-profiles" aria-labelledby="cx-profiles-title">
      <header className="cx-profiles__head">
        <div>
          <span className="cx-eyebrow"><UserRoundCog size={14} aria-hidden="true" />Demonstração</span>
          <h2 id="cx-profiles-title">Para quem a Valyra vai trabalhar hoje?</h2>
          <p className="app-muted">Escolha um cliente: cada perfil já usa a Valyra há alguns meses, com extrato, orçamento e alertas próprios. A Central, o menu, a faixa do topo, o radar e as perguntas à IA se ajustam a ele. Dados sintéticos.</p>
        </div>
        {chosen && onDone && <button type="button" className="button button--ghost button--sm" onClick={onDone}>Fechar</button>}
      </header>
      <ul className="cx-profiles__list">
        {PROFILES.map((p) => (
          <ProfileCard key={p.id} p={p} active={chosen && p.id === profile.id} onPick={() => { setProfile(p.id); onDone?.(); }} />
        ))}
      </ul>
    </section>
  );
};

/** Topo da Central: seletor até a escolha; depois, os atalhos do perfil. */
export const ProfileFocus: FC = () => {
  const { profile, chosen } = useProfile();
  const [picking, setPicking] = useState(false);
  if (!chosen || picking) return <Picker onDone={() => setPicking(false)} />;
  return (
    <section className="cx-foryou" aria-label={`Para você: perfil ${profile.name}`}>
      <div className="cx-foryou__who">
        <span className="cx-profile-avatar" aria-hidden="true">{profile.initial}</span>
        <span><small>Para você</small><b>{profile.name}</b></span>
        <button type="button" className="cx-foryou__switch" onClick={() => setPicking(true)}>Trocar perfil</button>
      </div>
      <ul className="cx-foryou__list">
        {profile.shortcuts.map((s) => {
          const { Icon, title } = MODULES[s.module];
          return (
            <li key={s.title}>
              <a className={`cx-shortcut cx-shortcut--${s.module}`} href={shortcutHref(s)}>
                <span className="cx-shortcut__icon" aria-hidden="true"><Icon size={16} /></span>
                <span><small>{title}</small><b>{s.title}</b><em>{s.hint}</em></span>
                <ArrowUpRight size={15} className="cx-shortcut__go" aria-hidden="true" />
              </a>
            </li>
          );
        })}
      </ul>
    </section>
  );
};

/** Menu de perfil no cabeçalho: troca de perfil de qualquer tela. */
export const ProfileMenu: FC = () => {
  const { profile, chosen, setProfile } = useProfile();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('pointerdown', onDown); document.removeEventListener('keydown', onKey); };
  }, [open]);

  return (
    <div className="cx-profile-menu" ref={ref}>
      <button
        type="button"
        className="cx-profile-menu__button"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Perfil da demonstração: ${chosen ? profile.name : 'não escolhido'}. Trocar perfil`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="cx-profile-avatar" aria-hidden="true">{chosen ? profile.initial : 'D'}</span>
        <span className="cx-profile-menu__name">{chosen ? profile.name : 'Escolher perfil'}</span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && (
        <div className="cx-profile-menu__panel" role="group" aria-label="Perfis da demonstração">
          <p>Perfil da demonstração</p>
          {PROFILES.map((p) => (
            <button key={p.id} type="button" aria-pressed={chosen && p.id === profile.id} onClick={() => { setProfile(p.id); setOpen(false); }}>
              <span className="cx-profile-avatar" aria-hidden="true">{p.initial}</span>
              <span><b>{p.name}</b><small>{p.plan}</small></span>
              {chosen && p.id === profile.id && <Check size={15} aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
