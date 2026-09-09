import React, { createContext, useContext, useEffect, useState } from 'react';

export type AccentTheme = 'cobalt' | 'indigo' | 'emerald' | 'violet' | 'amber';

interface ThemeContextType {
  accentColor: AccentTheme;
  setAccentColor: (color: AccentTheme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = 'codenter_accent_theme';

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [accentColor, setAccentState] = useState<AccentTheme>('cobalt');

  useEffect(() => {
    const saved = (localStorage.getItem(STORAGE_KEY) as AccentTheme) || 'cobalt';
    setAccentState(saved);
    applyThemeAttribute(saved);
  }, []);

  const applyThemeAttribute = (theme: AccentTheme) => {
    if (theme === 'cobalt') {
      document.documentElement.removeAttribute('data-accent');
    } else {
      document.documentElement.setAttribute('data-accent', theme);
    }
  };

  const setAccentColor = (theme: AccentTheme) => {
    setAccentState(theme);
    localStorage.setItem(STORAGE_KEY, theme);
    applyThemeAttribute(theme);
  };

  return (
    <ThemeContext.Provider value={{ accentColor, setAccentColor }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
