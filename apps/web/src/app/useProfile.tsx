import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { FC, ReactNode } from 'react';
import { NEUTRAL_PROFILE, findProfile, isTickerMode } from './profiles';
import type { Profile, TickerMode } from './profiles';

/*
 * Perfil escolhido e modo do ticker ficam no navegador de quem está vendo a demo: são
 * preferências de visualização, sem login nem dado pessoal. Em janela anônima ou com o
 * armazenamento bloqueado, o app funciona igual, só não lembra a escolha.
 */
const PROFILE_KEY = 'valyra:demo-profile';
const TICKER_KEY = 'valyra:ticker-mode';

function read(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch { /* sem armazenamento: a escolha vale só nesta visita */ }
}

type ProfileState = {
  /** Perfil escolhido, ou a experiência neutra enquanto ninguém escolheu. */
  profile: Profile;
  /** false até a pessoa escolher um perfil: a Central mostra o seletor. */
  chosen: boolean;
  setProfile: (id: string) => void;
  ticker: TickerMode;
  setTicker: (mode: TickerMode) => void;
};

const ProfileContext = createContext<ProfileState | null>(null);

export const ProfileProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [profileId, setProfileId] = useState(() => read(PROFILE_KEY));
  const [override, setOverride] = useState<TickerMode | null>(() => {
    const v = read(TICKER_KEY);
    return isTickerMode(v) ? v : null;
  });
  const saved = findProfile(profileId);
  const profile = saved ?? NEUTRAL_PROFILE;

  const setProfile = useCallback((id: string) => {
    setProfileId(id);
    write(PROFILE_KEY, id);
    // Trocar de perfil volta o ticker ao padrão do perfil: é o que a demo quer mostrar.
    setOverride(null);
    write(TICKER_KEY, null);
  }, []);
  const setTicker = useCallback((mode: TickerMode) => {
    setOverride(mode);
    write(TICKER_KEY, mode);
  }, []);

  const value = useMemo<ProfileState>(() => ({
    profile,
    chosen: saved !== null,
    setProfile,
    ticker: override ?? profile.ticker,
    setTicker,
  }), [profile, saved, override, setProfile, setTicker]);

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
};

export function useProfile(): ProfileState {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error('useProfile fora do ProfileProvider');
  return ctx;
}
