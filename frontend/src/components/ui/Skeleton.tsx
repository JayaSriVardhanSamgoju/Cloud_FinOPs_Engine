import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'bg-gradient-to-r from-card via-card-hover to-card bg-[length:200%_100%] animate-shimmer rounded-[12px]',
        className
      )}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-card border border-border rounded-[12px] p-5 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}
