import { playerPhotos } from '../media';
import { LocalImage } from './LocalImage';

export function PlayerHeadshot({
  nhlId,
  name,
  variant = 'roster',
}: {
  nhlId?: number;
  name: string;
  variant?: 'roster' | 'hero';
}) {
  const candidate = nhlId === undefined ? undefined : playerPhotos[nhlId];
  // IDs choose the asset; an exact canonical-name check rejects conflicting fixtures.
  const photo = candidate?.name === name ? candidate : undefined;
  return (
    <LocalImage
      key={photo?.src ?? `missing-${nhlId ?? name}`}
      src={photo?.src}
      name={name}
      kind="photo"
      fallback={name
        .split(' ')
        .map((word) => word[0])
        .join('')}
      className={`headshot headshot-${variant}`}
      style={
        photo
          ? ({
              '--photo-width': `${photo.zoom * 100}%`,
              '--photo-focus': `translate(-${photo.x}%, -${photo.y}%)`,
            } as React.CSSProperties)
          : undefined
      }
    />
  );
}
