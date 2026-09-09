import React from 'react';
import { useTheme, AccentTheme } from '../../context/ThemeContext';

interface ThemeOption {
  id: AccentTheme;
  name: string;
  colorHex: string;
}

const THEMES: ThemeOption[] = [
  { id: 'cobalt', name: 'Cobalt', colorHex: '#1D4ED8' },
  { id: 'indigo', name: 'Indigo', colorHex: '#4F46E5' },
  { id: 'emerald', name: 'Emerald', colorHex: '#059669' },
  { id: 'violet', name: 'Violet', colorHex: '#7C3AED' },
  { id: 'amber', name: 'Amber', colorHex: '#D97706' },
];

export const ThemePicker: React.FC = () => {
  const { accentColor, setAccentColor } = useTheme();

  return (
    <div className="flex items-center gap-1.5 p-1 bg-white/70 backdrop-blur-md border border-white/80 rounded-[14px] shadow-[var(--shadow-glass)]">
      {THEMES.map((t) => (
        <button
          key={t.id}
          onClick={() => setAccentColor(t.id)}
          title={`Switch accent to ${t.name}`}
          className={`w-5 h-5 rounded-full transition-all duration-200 ${
            accentColor === t.id
              ? 'scale-110 ring-2 ring-offset-1 ring-[var(--text-primary)] shadow-sm'
              : 'opacity-70 hover:opacity-100 hover:scale-105'
          }`}
          style={{ backgroundColor: t.colorHex }}
        />
      ))}
    </div>
  );
};
