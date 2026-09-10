import React, { useState } from 'react';
import {
  ChevronRight,
  Layers,
  LayoutDashboard,
  Users,
  Send,
  MessageSquare,
  Menu,
} from 'lucide-react';
import { ConsoleHeader } from './ui/ConsoleHeader';
import { CollapsibleSidebar, ConsoleTab } from './ui/CollapsibleSidebar';
import { WorkspacesView } from './WorkspacesView';
import { DashboardOverview } from './DashboardOverview';
import { LeadsView } from './LeadsView';
import { CampaignsView } from './CampaignsView';
import { SplitPaneInbox } from './SplitPaneInbox';
import { KnowledgeView } from './KnowledgeView';
import { IntegrationsView } from './IntegrationsView';
import { CalendarView } from './CalendarView';
import { AnalyticsView } from './AnalyticsView';
import { SettingsView } from './SettingsView';
import { useAuth } from '../context/AuthContext';

interface ConsoleLayoutProps {
  onGoToHome: () => void;
  initialTab?: ConsoleTab;
}

export const ConsoleLayout: React.FC<ConsoleLayoutProps> = ({
  onGoToHome,
  initialTab = 'workspaces',
}) => {
  const { workspace } = useAuth();
  const [activeTab, setActiveTab] = useState<ConsoleTab>(initialTab);
  const [activeWorkspaceName, setActiveWorkspaceName] = useState<string>(workspace?.name || 'AI SDR');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);
  const [newWsModalOpen, setNewWsModalOpen] = useState<boolean>(false);

  const tabLabels: Record<ConsoleTab, string> = {
    workspaces: 'Workspaces',
    overview: 'Overview',
    leads: 'Leads & Accounts',
    campaigns: 'Campaigns',
    inbox: 'Inbox',
    knowledge: 'Knowledge Base',
    integrations: 'Integrations',
    calendar: 'Calendar',
    analytics: 'Analytics',
    settings: 'Settings',
  };

  const handleSelectWorkspace = (_id: string, name: string, targetTab?: ConsoleTab) => {
    setActiveWorkspaceName(name);
    setActiveTab(targetTab || 'overview');
  };

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] font-sans flex flex-col">
      {/* 1. Full Top Header */}
      <ConsoleHeader
        onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
        onGoToHome={onGoToHome}
        onNavigateTab={(tab) => setActiveTab(tab as ConsoleTab)}
        activeWorkspaceName={activeWorkspaceName}
        onOpenNewWorkspaceModal={() => {
          setActiveTab('workspaces');
          setNewWsModalOpen(true);
        }}
      />

      {/* 2. Body Container with Collapsible Sidebar + Main View */}
      <div className="flex-1 flex items-start">
        {/* Hover-to-expand / Collapsible Sidebar */}
        <CollapsibleSidebar
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          mobileOpen={mobileSidebarOpen}
          onCloseMobile={() => setMobileSidebarOpen(false)}
          onGoToHome={onGoToHome}
        />

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 w-full p-4 sm:p-6 md:p-8 overflow-x-hidden pb-24 md:pb-8">
          {/* Breadcrumbs (shown when viewing a specific workspace tool) */}
          {activeTab !== 'workspaces' && (
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] font-medium mb-6 pb-3 border-b border-slate-200/70">
              <button
                type="button"
                onClick={() => setActiveTab('workspaces')}
                className="flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors font-semibold"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Workspaces</span>
              </button>
              <ChevronRight className="w-3 h-3 text-slate-300" />
              <span className="text-[var(--text-secondary)] font-semibold truncate max-w-[150px]">
                {activeWorkspaceName}
              </span>
              <ChevronRight className="w-3 h-3 text-slate-300" />
              <span className="text-[var(--accent-primary)] font-bold">
                {tabLabels[activeTab]}
              </span>
            </div>
          )}

          {/* View Components */}
          {activeTab === 'workspaces' && (
            <WorkspacesView
              onSelectWorkspace={handleSelectWorkspace}
              isCreateModalOpen={newWsModalOpen}
              onCloseCreateModal={() => setNewWsModalOpen(false)}
            />
          )}
          {activeTab === 'overview' && (
            <DashboardOverview onNavigate={(tab) => setActiveTab(tab as ConsoleTab)} />
          )}
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

      {/* 3. Mobile Native Web App Bottom Tab Bar */}
      <nav
        aria-label="Mobile Navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white/90 backdrop-blur-xl border-t border-white/80 py-1.5 px-2 flex items-center justify-around shadow-[0_-4px_20px_rgba(0,0,0,0.06)]"
      >
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`flex flex-col items-center gap-0.5 py-1 px-2.5 rounded-[12px] transition-all ${
            activeTab === 'overview'
              ? 'text-[var(--accent-primary)] font-bold'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <LayoutDashboard className="w-5 h-5" />
          <span className="text-[10px]">Overview</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('leads')}
          className={`flex flex-col items-center gap-0.5 py-1 px-2.5 rounded-[12px] transition-all ${
            activeTab === 'leads'
              ? 'text-[var(--accent-primary)] font-bold'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <Users className="w-5 h-5" />
          <span className="text-[10px]">Leads</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('campaigns')}
          className={`flex flex-col items-center gap-0.5 py-1 px-2.5 rounded-[12px] transition-all ${
            activeTab === 'campaigns'
              ? 'text-[var(--accent-primary)] font-bold'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <Send className="w-5 h-5" />
          <span className="text-[10px]">Campaigns</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('inbox')}
          className={`flex flex-col items-center gap-0.5 py-1 px-2.5 rounded-[12px] transition-all ${
            activeTab === 'inbox'
              ? 'text-[var(--accent-primary)] font-bold'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <MessageSquare className="w-5 h-5" />
          <span className="text-[10px]">Inbox</span>
        </button>

        <button
          type="button"
          onClick={() => setMobileSidebarOpen(true)}
          className={`flex flex-col items-center gap-0.5 py-1 px-2.5 rounded-[12px] transition-all ${
            ['workspaces', 'knowledge', 'integrations', 'calendar', 'analytics', 'settings'].includes(activeTab)
              ? 'text-[var(--accent-primary)] font-bold'
              : 'text-slate-400 hover:text-slate-600'
          }`}
        >
          <Menu className="w-5 h-5" />
          <span className="text-[10px]">More</span>
        </button>
      </nav>
    </div>
  );
};
