import React, { useState } from 'react';

interface ScoreReason {
  category: string;
  points: number;
  reason: string;
}

interface ICPScoreGaugeProps {
  score: number;
  scoreBand?: string;
  reasons?: ScoreReason[];
  size?: 'sm' | 'md' | 'lg';
}

export const ICPScoreGauge: React.FC<ICPScoreGaugeProps> = ({
  score,
  scoreBand,
  reasons = [],
  size = 'md',
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  // Band calculations
  const band = scoreBand || (score >= 80 ? 'HOT' : score >= 50 ? 'WARM' : 'COLD');
  
  const bandColor =
    band === 'HOT'
      ? { text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300', stroke: '#059669' }
      : band === 'WARM'
      ? { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-300', stroke: '#D97706' }
      : { text: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-300', stroke: '#64748B' };

  // SVG dimensions
  const dim = size === 'sm' ? 44 : size === 'lg' ? 84 : 58;
  const strokeWidth = size === 'sm' ? 4 : size === 'lg' ? 7 : 5;
  const radius = (dim - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  return (
    <div
      className="relative inline-flex items-center justify-center cursor-pointer select-none"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <svg width={dim} height={dim} className="transform -rotate-90">
        {/* Background track circle */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          stroke="rgba(226, 232, 240, 0.7)"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Animated score arc */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          stroke={bandColor.stroke}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
        />
      </svg>

      {/* Center Label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={`font-black ${
            size === 'sm' ? 'text-[11px]' : size === 'lg' ? 'text-xl' : 'text-sm'
          } ${bandColor.text}`}
        >
          {Math.round(score)}
        </span>
        {size === 'lg' && (
          <span className="text-[9px] font-bold tracking-wider uppercase text-[var(--text-muted)]">
            {band}
          </span>
        )}
      </div>

      {/* Reason Breakdown Popover */}
      {showTooltip && reasons.length > 0 && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 p-3 bg-white/95 backdrop-blur-2xl border border-white/90 rounded-[18px] shadow-[var(--shadow-glass-elevated)] z-50 pointer-events-none text-left">
          <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 mb-2">
            <span className="text-xs font-bold text-[var(--text-primary)]">ICP Score Analysis</span>
            <span className={`px-1.5 py-0.5 rounded-[6px] text-[10px] font-bold ${bandColor.bg} ${bandColor.text} border ${bandColor.border}`}>
              {band} ({score}/100)
            </span>
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {reasons.map((r, i) => (
              <div key={i} className="flex items-start justify-between gap-2 text-[11px]">
                <span className="text-[var(--text-secondary)] leading-tight">{r.reason}</span>
                <span className={`font-bold shrink-0 ${r.points >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {r.points > 0 ? `+${r.points}` : r.points}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
