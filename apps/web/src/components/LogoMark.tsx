import { useId } from 'react';
import type { FC } from 'react';

/**
 * Marca oficial da Valyra: V em três lâminas com degradê azul-royal → ciano.
 * Fonte única para landing, app e favicon (public/favicon.svg usa os mesmos traços).
 */
export const LOGO_PATHS = [
  // Haste esquerda: termina na diagonal da lâmina inferior, que a sobrepõe.
  'M343 485H466C496 485 520 498 537 522L683 723L603 826C599 830 593 830 590 826Z',
  // Lâmina superior direita.
  'M683 627L786 495C791 488 798 485 807 485H917L823 614C817 622 810 627 800 627Z',
  // Lâmina inferior direita.
  'M735 656H802L683 820C678 826 672 828 664 828H600Z',
];

export const LogoMark: FC<{ size?: number; className?: string }> = ({ size = 24, className }) => {
  // useId evita colisão de gradientes quando a marca aparece mais de uma vez na página.
  const id = useId().replace(/:/g, '');
  return (
    <svg className={className} width={size} height={size} viewBox="330 357 600 600" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-a`} gradientUnits="userSpaceOnUse" x1="560" y1="828" x2="900" y2="470">
          <stop offset="0" stopColor="#0a3fe0" />
          <stop offset="0.55" stopColor="#2f86ff" />
          <stop offset="1" stopColor="#52d4ff" />
        </linearGradient>
        <linearGradient id={`${id}-b`} gradientUnits="userSpaceOnUse" x1="360" y1="480" x2="640" y2="840">
          <stop offset="0" stopColor="#1f6bff" />
          <stop offset="0.6" stopColor="#2a8bff" />
          <stop offset="1" stopColor="#0b45ea" />
        </linearGradient>
      </defs>
      <path d={LOGO_PATHS[0]} fill={`url(#${id}-b)`} />
      <path d={LOGO_PATHS[1]} fill={`url(#${id}-a)`} />
      <path d={LOGO_PATHS[2]} fill={`url(#${id}-a)`} />
    </svg>
  );
};
