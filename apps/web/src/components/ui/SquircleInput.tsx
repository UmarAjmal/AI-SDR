import React, { InputHTMLAttributes } from 'react';

interface SquircleInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const SquircleInput: React.FC<SquircleInputProps> = ({
  label,
  error,
  icon,
  className = '',
  ...props
}) => {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <div className="absolute left-3.5 text-[var(--text-muted)] pointer-events-none flex items-center">
            {icon}
          </div>
        )}
        <input
          className={`w-full bg-white/70 backdrop-blur-md border border-white/80 rounded-[16px] px-4 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] shadow-[var(--shadow-glass)] outline-none transition-all duration-200 focus:bg-white/90 focus:ring-4 focus:ring-[var(--accent-glow)] focus:border-[var(--accent-border)] ${
            icon ? 'pl-10' : ''
          } ${error ? 'border-red-400 ring-2 ring-red-100' : ''} ${className}`}
          {...props}
        />
      </div>
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
        className={`w-full bg-white/70 backdrop-blur-md border border-white/80 rounded-[16px] p-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] shadow-[var(--shadow-glass)] outline-none transition-all duration-200 focus:bg-white/90 focus:ring-4 focus:ring-[var(--accent-glow)] focus:border-[var(--accent-border)] resize-y ${
          error ? 'border-red-400 ring-2 ring-red-100' : ''
        } ${className}`}
        {...props}
      />
      {error && <span className="text-xs text-red-500 font-medium">{error}</span>}
    </div>
  );
};
