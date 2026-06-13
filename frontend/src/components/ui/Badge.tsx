import clsx from 'clsx';

interface BadgeProps {
  variant: 'success' | 'warning' | 'danger' | 'accent' | 'info' | 'neutral';
  children: React.ReactNode;
  pulse?: boolean;
  size?: 'sm' | 'md';
}

const variantStyles: Record<string, string> = {
  success: 'bg-success/15 text-success border-success/30',
  warning: 'bg-warning/15 text-warning border-warning/30',
  danger: 'bg-danger/15 text-danger border-danger/30',
  accent: 'bg-accent/15 text-accent border-accent/30',
  info: 'bg-info/15 text-info border-info/30',
  neutral: 'bg-white/5 text-text-secondary border-white/10',
};

export function Badge({ variant, children, pulse = false, size = 'sm' }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 border rounded-[6px] font-semibold uppercase tracking-wider',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs',
        variantStyles[variant],
        pulse && 'animate-pulse-live'
      )}
    >
      {pulse && (
        <span className={clsx('w-1.5 h-1.5 rounded-full', {
          'bg-success': variant === 'success',
          'bg-warning': variant === 'warning',
          'bg-danger': variant === 'danger',
          'bg-accent': variant === 'accent',
          'bg-info': variant === 'info',
        })} />
      )}
      {children}
    </span>
  );
}
