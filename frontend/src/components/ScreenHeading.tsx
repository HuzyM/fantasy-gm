import type { ReactNode } from 'react';
export function ScreenHeading({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="screen-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="screen-tools">{children}</div>
    </header>
  );
}
