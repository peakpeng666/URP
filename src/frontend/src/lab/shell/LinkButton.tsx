import type { AnchorHTMLAttributes } from 'react';
import type { LucideIcon } from 'lucide-react';
import m from '../ui/mac.module.css';

/** An anchor styled as the shared macOS button (navigation and downloads). */
export function LinkButton({
  icon: Icon,
  size = 'md',
  variant = 'secondary',
  disabled = false,
  children,
  className,
  ...rest
}: {
  icon?: LucideIcon;
  size?: 'sm' | 'md';
  variant?: 'primary' | 'secondary' | 'plain';
  disabled?: boolean;
} & AnchorHTMLAttributes<HTMLAnchorElement>) {
  const cls = [m.button, size === 'sm' && m.sm, variant !== 'secondary' && m[variant], !children && m.iconOnly, className]
    .filter(Boolean)
    .join(' ');
  return (
    <a
      {...rest}
      href={disabled ? undefined : rest.href}
      aria-disabled={disabled || undefined}
      className={cls}
      style={{ textDecoration: 'none', ...(disabled ? { opacity: 0.45, pointerEvents: 'none' } : null), ...rest.style }}
    >
      {Icon && <Icon size={size === 'sm' ? 13 : 15} strokeWidth={1.9} aria-hidden />}
      {children}
    </a>
  );
}
