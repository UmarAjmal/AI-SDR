import React, { InputHTMLAttributes } from 'react';

interface SquircleInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const SquircleInput: React.FC<SquircleInputProps> = ({
  label,
  error,
  hint,
  icon,
  leftIcon,
  rightIcon,
  className = '',
  ...props
}) => {
  const effectiveLeftIcon = leftIcon || icon;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {effectiveLeftIcon && (
          <div className="absolute left-3.5 text-[var(--text-muted)] pointer-events-none flex items-center">
            {effectiveLeftIcon}
          </div>
        )}
        <input
          className={`w-full bg-slate-50/80 hover:bg-white focus:bg-white border border-slate-200/90 hover:border-slate-300 rounded-[14px] px-3.5 py-2.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 shadow-2xs outline-none transition-all duration-200 focus:ring-2 focus:ring-[var(--accent-glow)] focus:border-[var(--accent-primary)] ${
            effectiveLeftIcon ? 'pl-10' : ''
          } ${rightIcon ? 'pr-10' : ''} ${error ? 'border-red-400 ring-2 ring-red-100' : ''} ${className}`}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3.5 flex items-center">
            {rightIcon}
          </div>
        )}
      </div>
      {hint && !error && <span className="text-[11px] text-[var(--text-muted)] font-medium">{hint}</span>}
      {error && <span className="text-xs text-red-500 font-medium">{error}</span>}
    </div>
  );
};

interface SquircleTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const SquircleTextarea: React.FC<SquircleTextareaProps> = ({
  label,
  error,
  className = '',
  rows = 4,
  ...props
}) => {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          {label}
        </label>
      )}
      <textarea
        rows={rows}
        className={`w-full bg-slate-50/80 hover:bg-white focus:bg-white border border-slate-200/90 hover:border-slate-300 rounded-[14px] p-3.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 shadow-2xs outline-none transition-all duration-200 focus:ring-2 focus:ring-[var(--accent-glow)] focus:border-[var(--accent-primary)] resize-y ${
          error ? 'border-red-400 ring-2 ring-red-100' : ''
        } ${className}`}
        {...props}
      />
      {error && <span className="text-xs text-red-500 font-medium">{error}</span>}
    </div>
  );
};
