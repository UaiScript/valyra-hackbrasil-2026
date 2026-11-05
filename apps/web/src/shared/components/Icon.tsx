import type { CSSProperties } from 'react';

const paths = {
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  overview: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  finance: 'M4 5h16v15H4zM4 10h16M8 15h3m4 0h1M8 2v5m8-5v5',
  planning: 'M4 20h16M7 16v-4m5 4V8m5 8V4',
  radar: 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12l8-8',
  person: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  business: 'M4 21V5h10v16m0-12h6v12M2 21h20M8 9h2m-2 4h2m-2 4h2m7-4h1m-1 4h1',
  external: 'M14 3h7v7m0-7L10 14M10 3H3v18h18v-7',
  plus: 'M12 5v14M5 12h14',
  check: 'm5 12 4 4L19 6',
  info: 'M12 8h.01M12 11v6M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
  chevron: 'm6 9 6 6 6-6',
  search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
} as const;

export function Icon({
  name,
  size = 20,
  style,
}: {
  name: keyof typeof paths;
  size?: number;
  style?: CSSProperties;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={style}
    >
      <path d={paths[name]} />
    </svg>
  );
}

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <a
      className={`brand${light ? ' brand-light' : ''}`}
      href="#/"
      aria-label="Valyra, página inicial"
    >
      <svg viewBox="0 0 40 40" width="36" height="36" aria-hidden="true">
        <circle cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeWidth="2.2" />
        <path d="m10 29 8-20 13 3-21 17Z" fill="var(--coral)" />
        <circle cx="20" cy="20" r="3" fill="currentColor" />
      </svg>
      <span>
        valyra<span className="brand-dot">.</span>
      </span>
    </a>
  );
}
