import React, { useState } from 'react';
import { LogOut, User, Building, ArrowLeft } from 'lucide-react';
import { SquircleButton } from './components/ui/SquircleButton';
import { ThemePicker } from './components/ui/ThemePicker';
import { DashboardOverview } from './components/DashboardOverview';
import { LeadsView } from './components/LeadsView';
import { CampaignsView } from './components/CampaignsView';
import { SplitPaneInbox } from './components/SplitPaneInbox';
import { KnowledgeView } from './components/KnowledgeView';
import { IntegrationsView } from './components/IntegrationsView';
import { CalendarView } from './components/CalendarView';
import { AnalyticsView } from './components/AnalyticsView';
import { SettingsView } from './components/SettingsView';
import { HomePage } from './components/HomePage';
import { useAuth } from './context/AuthContext';

type NavTab =
  | 'overview'
  | 'leads'
  | 'campaigns'
  | 'inbox'
  | 'knowledge'
  | 'integrations'
  | 'calendar'
  | 'analytics'
  | 'settings';

const NAV_ITEMS: { id: NavTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'leads', label: 'Leads' },
  { id: 'campaigns', label: 'Campaigns' },
  { id: 'inbox', label: 'Inbox' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'integrations', label: 'Integrations' },
  { id: 'calendar', label: 'Calendar' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'settings', label: 'Settings' },
];

export const App: React.FC = () => {
  const { isAuthenticated, user, workspace, logout, isLoading } = useAuth();
  const [currentView, setCurrentView] = useState<'home' | 'console'>('home');
  const [activeTab, setActiveTab] = useState<NavTab>('overview');

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

  // 1. Home Page View (Default)
  if (currentView === 'home') {
    return (
      <HomePage
        onGoToConsole={() => {
          if (isAuthenticated) {
            setCurrentView('console');
          }
        }}
      />
    );
  }

  // 2. Console View (SDR Operations Dashboard)
  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] font-sans">
      {/* Top Frosted Navbar */}
      <header className="sticky top-0 z-50 bg-white/75 backdrop-blur-xl border-b border-white/80 shadow-[var(--shadow-glass)] px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Brand Logo & Squircle Monogram + Back to Home */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentView('home')}
              title="Return to Home Page"
              className="flex items-center gap-2 p-1.5 -ml-1.5 rounded-[14px] hover:bg-slate-100/80 transition-all text-[var(--text-secondary)] hover:text-[var(--text-primary)] group"
            >
              <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
              <span className="hidden sm:inline text-xs font-bold text-slate-500 group-hover:text-slate-900">
                Home
              </span>
            </button>

            <div className="h-4 w-[1px] bg-slate-200" />

            <div
              className="flex items-center gap-2.5 cursor-pointer"
              onClick={() => setActiveTab('overview')}
            >
              <div className="w-9 h-9 rounded-[12px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-xs flex items-center justify-center border border-[var(--accent-border)] shadow-xs">
                SDR
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-1.5">
                  Codenter Console
                  <span className="px-1.5 py-0.5 rounded-[8px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] text-[9px] font-black border border-[var(--accent-border)]">
                    PRO
                  </span>
                </h1>
                <p className="text-[10px] text-[var(--text-muted)] font-medium">
                  Autonomous Sales Engine
                </p>
              </div>
            </div>
          </div>

          {/* Navigation Items (Apple Squircles) */}
          <nav className="hidden md:flex items-center gap-1 bg-white/50 backdrop-blur-md p-1 rounded-[16px] border border-white/70">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all duration-200 ${
                  activeTab === item.id
                    ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/60'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {/* User Profile, Workspace & Theme Actions */}
          <div className="flex items-center gap-2.5">
            <ThemePicker />

            {/* Active Workspace Pill */}
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] bg-white/70 border border-slate-200/70 text-xs font-medium text-slate-700">
              <Building className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-semibold text-slate-800 truncate max-w-[140px]">
                {workspace?.name || 'Workspace'}
              </span>
            </div>

            {/* User Avatar Monogram */}
            <div
              className="flex items-center gap-2 pl-2 border-l border-slate-200/70"
              title={`Logged in as ${user?.email}`}
            >
              <div className="w-8 h-8 rounded-[10px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-bold text-xs flex items-center justify-center border border-[var(--accent-border)]">
                {user?.email ? user.email.charAt(0).toUpperCase() : <User className="w-3.5 h-3.5" />}
              </div>

              {/* Sign Out Button */}
              <SquircleButton
                variant="ghost"
                size="sm"
                onClick={() => {
                  logout();
                  setCurrentView('home');
                }}
                className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50"
                title="Sign Out of Session"
              >
                <LogOut className="w-4 h-4" />
              </SquircleButton>
            </div>
          </div>
        </div>
      </header>

      {/* Main Console Container */}
      <main className="max-w-7xl mx-auto p-6 md:p-8">
        {activeTab === 'overview' && <DashboardOverview onNavigate={(tab) => setActiveTab(tab as NavTab)} />}
        {activeTab === 'leads' && <LeadsView />}
        {activeTab === 'campaigns' && <CampaignsView />}
        {activeTab === 'inbox' && <SplitPaneInbox />}
        {activeTab === 'knowledge' && <KnowledgeView />}
        {activeTab === 'integrations' && <IntegrationsView />}
        {activeTab === 'calendar' && <CalendarView />}
        {activeTab === 'analytics' && <AnalyticsView />}
        {activeTab === 'settings' && <SettingsView />}
      </main>
    </div>
  );
};

export default App;
