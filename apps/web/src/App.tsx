import React, { useState } from 'react';
import { HomePage } from './components/HomePage';
import { ConsoleLayout } from './components/ConsoleLayout';
import { useAuth } from './context/AuthContext';

export const App: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentView, setCurrentView] = useState<'home' | 'console'>('home');

  // Loading Session Skeleton
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg-canvas)] flex items-center justify-center">
        <div className="p-8 rounded-[24px] bg-white/70 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-[14px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-sm flex items-center justify-center border border-[var(--accent-border)] animate-pulse">
            SDR
          </div>
          <p className="text-xs font-semibold text-[var(--text-secondary)]">
            Authenticating Session...
          </p>
        </div>
      </div>
    );
  }

  // 1. Console View (Authenticated SDR Operations Dashboard with Sidebar & Workspaces)
  if (currentView === 'console' && isAuthenticated) {
    return (
      <ConsoleLayout
        onGoToHome={() => setCurrentView('home')}
      />
    );
  }

  // 2. Home Page View (Default Landing Page with AuthModal, Hero, & Console Link)
  return (
    <HomePage
      onGoToConsole={() => {
        if (isAuthenticated) {
          setCurrentView('console');
        }
      }}
    />
  );
};

export default App;
