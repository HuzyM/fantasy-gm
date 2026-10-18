import { useState } from 'react';
import type { CSSProperties } from 'react';

/** Local, identity-mapped assets only. Key by source when the selected identity changes. */
export function LocalImage({
  src,
  name,
  kind,
  fallback,
  className,
  style,
}: {
  src?: string;
  name: string;
  kind: 'photo' | 'logo';
  fallback: string;
  className: string;
  style?: CSSProperties;
}) {
  const [state, setState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const available = !!src && state !== 'error';
  const label = `${name}: ${kind} ${available ? 'loading' : 'unavailable'}`;
  return (
    <span
      className={className}
      data-image-state={src ? state : 'missing'}
      aria-busy={available && state === 'loading'}
      style={style}
    >
      {available && (
        <img
          src={src}
          alt={`${name} ${kind === 'photo' ? 'photograph' : 'logo'}`}
          aria-hidden={state !== 'loaded'}
          decoding="async"
          onLoad={() => setState('loaded')}
          onError={() => setState('error')}
        />
      )}
      {(!available || state !== 'loaded') && (
        <span className="image-fallback" role="img" aria-label={label}>
          {fallback}
        </span>
      )}
    </span>
  );
}
