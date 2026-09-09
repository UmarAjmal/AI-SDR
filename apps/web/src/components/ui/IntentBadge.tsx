import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type IntentType =
  | 'POSITIVE_INTEREST'
  | 'PRICING'
  | 'PRODUCT_QUESTION'
  | 'OBJECTION'
  | 'REQUEST_INFO'
  | 'NOT_INTERESTED'
  | 'UNSUBSCRIBE'
  | 'WRONG_PERSON'
  | 'REFERRAL'
  | 'TIMING'
  | 'MEETING_REQUEST'
  | 'HUMAN_REQUEST'
  | 'OUT_OF_SCOPE'
  | 'AUTO_REPLY';

interface IntentBadgeProps {
  intent: IntentType | string;
  confidence?: number;
  showConfidence?: boolean;
  className?: string;
}

interface IntentConfig {
  label: string;
  dotColor: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  glowColor: string;
}

const INTENT_CONFIGS: Record<string, IntentConfig> = {
  POSITIVE_INTEREST: {
    label: 'Positive Interest',
    dotColor: 'bg-emerald-500',
    bgColor: 'bg-emerald-50/80',
    textColor: 'text-emerald-700',
    borderColor: 'border-emerald-200/80',
    glowColor: 'shadow-emerald-500/20',
  },
  MEETING_REQUEST: {
    label: 'Meeting Booked',
    dotColor: 'bg-blue-600',
    bgColor: 'bg-blue-50/80',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200/80',
    glowColor: 'shadow-blue-500/25',
  },
  PRICING: {
    label: 'Pricing Inquiry',
    dotColor: 'bg-violet-600',
    bgColor: 'bg-violet-50/80',
    textColor: 'text-violet-700',
    borderColor: 'border-violet-200/80',
    glowColor: 'shadow-violet-500/20',
  },
  PRODUCT_QUESTION: {
    label: 'Product Question',
    dotColor: 'bg-sky-500',
    bgColor: 'bg-sky-50/80',
    textColor: 'text-sky-700',
    borderColor: 'border-sky-200/80',
    glowColor: 'shadow-sky-500/20',
  },
  REQUEST_INFO: {
    label: 'Request Info',
    dotColor: 'bg-indigo-500',
    bgColor: 'bg-indigo-50/80',
    textColor: 'text-indigo-700',
    borderColor: 'border-indigo-200/80',
    glowColor: 'shadow-indigo-500/20',
  },
  REFERRAL: {
    label: 'Colleague Referral',
    dotColor: 'bg-teal-500',
    bgColor: 'bg-teal-50/80',
    textColor: 'text-teal-700',
    borderColor: 'border-teal-200/80',
    glowColor: 'shadow-teal-500/20',
  },
  TIMING: {
    label: 'Timing Later',
    dotColor: 'bg-amber-500',
    bgColor: 'bg-amber-50/80',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200/80',
    glowColor: 'shadow-amber-500/20',
  },
  WRONG_PERSON: {
    label: 'Wrong Person',
    dotColor: 'bg-slate-400',
    bgColor: 'bg-slate-50/80',
    textColor: 'text-slate-600',
    borderColor: 'border-slate-200/80',
    glowColor: 'shadow-slate-400/20',
  },
  NOT_INTERESTED: {
    label: 'Not Interested',
    dotColor: 'bg-zinc-400',
    bgColor: 'bg-zinc-100/80',
    textColor: 'text-zinc-600',
    borderColor: 'border-zinc-200/80',
    glowColor: 'shadow-zinc-400/20',
  },
  OBJECTION: {
    label: 'Objection Raised',
    dotColor: 'bg-orange-500',
    bgColor: 'bg-orange-50/80',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-200/80',
    glowColor: 'shadow-orange-500/20',
  },
  HUMAN_REQUEST: {
    label: 'Human Requested',
    dotColor: 'bg-purple-600',
    bgColor: 'bg-purple-50/80',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200/80',
    glowColor: 'shadow-purple-500/25',
  },
  OUT_OF_SCOPE: {
    label: 'Out of Scope',
    dotColor: 'bg-rose-500',
    bgColor: 'bg-rose-50/80',
    textColor: 'text-rose-700',
    borderColor: 'border-rose-200/80',
    glowColor: 'shadow-rose-500/20',
  },
  UNSUBSCRIBE: {
    label: 'Unsubscribed',
    dotColor: 'bg-red-600',
    bgColor: 'bg-red-50/90',
    textColor: 'text-red-700',
    borderColor: 'border-red-200/90',
    glowColor: 'shadow-red-600/30',
  },
  AUTO_REPLY: {
    label: 'Auto Reply (OOO)',
    dotColor: 'bg-cyan-500',
    bgColor: 'bg-cyan-50/80',
    textColor: 'text-cyan-700',
    borderColor: 'border-cyan-200/80',
    glowColor: 'shadow-cyan-500/20',
  },
};

export const IntentBadge: React.FC<IntentBadgeProps> = ({
  intent,
  confidence,
  showConfidence = false,
  className,
}) => {
  const normalizedKey = (intent || 'PRODUCT_QUESTION').toUpperCase();
  const config = INTENT_CONFIGS[normalizedKey] || {
    label: intent,
    dotColor: 'bg-slate-400',
    bgColor: 'bg-slate-50/80',
    textColor: 'text-slate-600',
    borderColor: 'border-slate-200/80',
    glowColor: 'shadow-slate-400/20',
  };

  return (
    <span
      className={twMerge(
        clsx(
          'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-[12px] backdrop-blur-md border shadow-sm transition-all duration-150',
          config.bgColor,
          config.textColor,
          config.borderColor,
          config.glowColor,
          className
        )
      )}
      title={`Intent: ${config.label}${confidence !== undefined ? ` (Confidence: ${Math.round(confidence * 100)}%)` : ''}`}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full shadow-sm', config.dotColor)} />
      <span>{config.label}</span>
      {showConfidence && confidence !== undefined && (
        <span className="opacity-70 text-[10px] ml-0.5">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
};
