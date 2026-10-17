import type { ButtonHTMLAttributes, ReactNode } from 'react';
import type { Datum } from '../view-model';
import { describeDatum } from '../view-model';

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}
export function Button({
  children,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={`button ${className}`} {...props}>
      {children}
    </button>
  );
}
export function DataValue<T>({
  datum,
  format,
  className = '',
}: {
  datum: Datum<T>;
  format?: (value: T) => string;
  className?: string;
}) {
  const { text, note } = describeDatum(datum, format);
  return (
    <span
      className={`data-value ${datum.state} ${className}`}
      title={note}
      data-certainty={datum.state}
    >
      {text}
      {note && <span className="sr-only">: {note}</span>}
    </span>
  );
}

const teamColors: Readonly<Record<string, string>> = {
  TOR: '#1771ce',
  BUF: '#f1bd30',
  BOS: '#f0bb39',
  DET: '#ee3344',
  NYR: '#246bd3',
  CBJ: '#dc243c',
  COL: '#a84561',
  EDM: '#ff7d31',
  TBL: '#3675df',
  FLA: '#caa259',
  DAL: '#21b59b',
  WPG: '#b9cde6',
  MIN: '#289a70',
  VGK: '#b9a36b',
  SJS: '#23c3c5',
  VAN: '#45a67b',
  ANA: '#d89854',
  LAK: '#c3cbd2',
};

/** Original typographic club marks, not official NHL logos. */
export function TeamMark({ code, large = false }: { code: string; large?: boolean }) {
  return (
    <span
      className={`team-mark ${large ? 'large' : ''}`}
      style={{ '--team-color': teamColors[code] ?? '#a6c1d4' } as React.CSSProperties}
      aria-hidden="true"
    >
      {code === 'TOR'
        ? '♠'
        : code === 'TBL'
          ? 'ϟ'
          : code === 'COL'
            ? 'A'
            : code === 'BOS'
              ? 'B'
              : code.slice(0, 2)}
    </span>
  );
}

export function PlayerAvatar({ index, name }: { index: number; name: string }) {
  if (index < 0)
    return (
      <span className="avatar avatar-fallback" aria-hidden="true">
        {name
          .split(' ')
          .map((word) => word[0])
          .join('')}
      </span>
    );
  return (
    <span
      className="avatar"
      role="img"
      aria-label={`${name}, synthetic portrait`}
      style={{ backgroundPosition: `${(index % 3) * 50}% ${index < 3 ? 0 : 100}%` }}
    />
  );
}
