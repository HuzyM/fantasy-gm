import type { ButtonHTMLAttributes, ReactNode } from 'react';
import type { Datum } from '../view-model';
import { describeDatum } from '../view-model';
import { teamAssets } from '../media';
import { LocalImage } from './LocalImage';

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

/** Centralized official team identity, sizing and fallback behavior. */
export function TeamMark({ code, large = false }: { code: string; large?: boolean }) {
  const team = teamAssets[code];
  return (
    <span title={team ? `${team.name} · official NHL team logo` : 'Team identity unavailable'}>
      <LocalImage
        key={team?.logo ?? code}
        src={team?.logo}
        name={team?.name ?? code}
        kind="logo"
        fallback={code}
        className={`team-mark ${large ? 'large' : ''}`}
      />
    </span>
  );
}
