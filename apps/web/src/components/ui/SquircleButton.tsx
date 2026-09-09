import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface SquircleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'frosted' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const SquircleButton: React.FC<SquircleButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  className,
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-[18px] transition-all duration-200 ease-out active:scale-[0.98] focus:outline-none disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100';

  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3.5 text-base',
  };

  const variantStyles = {
    primary: 'bg-[var(--accent-primary)] hover:bg-[var(--accent-hover)] text-white shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.35)] shadow-md hover:shadow-[0_4px_14px_0_var(--accent-glow)]',
    frosted: 'bg-white/80 hover:bg-white/95 backdrop-blur-md border border-white/80 text-slate-800 shadow-[var(--shadow-glass)] shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.95)]',
    outline: 'border border-slate-200 hover:border-[var(--accent-primary)] hover:bg-[var(--accent-subtle)] text-slate-700 hover:text-[var(--accent-primary)]',
    ghost: 'hover:bg-slate-100/70 text-slate-600 hover:text-slate-900',
    danger: 'bg-rose-500 hover:bg-rose-600 text-white shadow-md shadow-rose-500/20',
  };

  return (
    <button
      className={twMerge(clsx(baseStyles, sizeStyles[size], variantStyles[variant], className))}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block animate-spin mr-2 w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
      ) : null}
      {children}
    </button>
  );
};
