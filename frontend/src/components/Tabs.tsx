import { useRef } from 'react';
import type { ReactNode } from 'react';

/** Automatic-activation tabs with roving focus, shared by roster and inspection. */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  label,
  idPrefix,
  panelId,
  className,
}: {
  items: readonly { value: T; label: ReactNode }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  idPrefix: string;
  panelId: string;
  className: string;
}) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  return (
    <div className={className} role="tablist" aria-label={label}>
      {items.map((item, index) => (
        <button
          key={item.value}
          ref={(node) => {
            buttons.current[index] = node;
          }}
          id={`${idPrefix}-${item.value.replace(' ', '-')}`}
          role="tab"
          aria-controls={panelId}
          aria-selected={value === item.value}
          tabIndex={value === item.value ? 0 : -1}
          onClick={() => onChange(item.value)}
          onKeyDown={(event) => {
            let next: number;
            switch (event.key) {
              case 'ArrowRight':
                next = (index + 1) % items.length;
                break;
              case 'ArrowLeft':
                next = (index - 1 + items.length) % items.length;
                break;
              case 'Home':
                next = 0;
                break;
              case 'End':
                next = items.length - 1;
                break;
              default:
                return;
            }
            event.preventDefault();
            const target = items[next];
            if (target) {
              onChange(target.value);
              buttons.current[next]?.focus();
            }
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
