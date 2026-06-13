import clsx from 'clsx';

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
}

export function Select({ value, onChange, options, className }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={clsx(
        'bg-card border border-border rounded-[8px] px-3 py-1.5',
        'text-text-primary text-sm font-medium',
        'focus:outline-none focus:border-accent',
        'cursor-pointer transition-colors',
        'appearance-none',
        className
      )}
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238B8D97' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 8px center',
        paddingRight: '28px',
      }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-card text-text-primary">
          {opt.label}
        </option>
      ))}
    </select>
  );
}
