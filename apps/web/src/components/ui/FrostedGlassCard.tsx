import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface FrostedGlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  elevated?: boolean;
}

export const FrostedGlassCard: React.FC<FrostedGlassCardProps> = ({
  children,
  className,
  elevated = false,
  ...props
}) => {
  return (
    <div
      className={twMerge(
        clsx(
          'bg-white/75 backdrop-blur-xl border border-white/80 rounded-[24px] p-6 shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.95)] transition-all duration-200',
          elevated
            ? 'shadow-[var(--shadow-glass-elevated)] bg-white/85'
            : 'shadow-[var(--shadow-glass)]',
          className
        )
      )}
      {...props}
    >
      {children}
    </div>
  );
};
