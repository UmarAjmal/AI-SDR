import React, { useState } from 'react';
import {
  Layers,
  LayoutDashboard,
  Users,
  Send,
  MessageSquare,
  BookOpen,
  PlugZap,
  Calendar,
  BarChart3,
  Settings,
  Pin,
  Home,
  X
} from 'lucide-react';

export type ConsoleTab =
  | 'workspaces'
  | 'overview'
  | 'leads'
  | 'campaigns'
  | 'inbox'
  | 'knowledge'
  | 'integrations'
  | 'calendar'
  | 'analytics'
  | 'settings';

interface CollapsibleSidebarProps {
  activeTab: ConsoleTab;
  onSelectTab: (tab: ConsoleTab) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onGoToHome: () => void;
}

interface NavItem {
  id: ConsoleTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'workspaces', label: 'Workspaces', icon: Layers, badge: 'Hub' },
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'leads', label: 'Leads & Accounts', icon: Users },
  { id: 'campaigns', label: 'Campaigns', icon: Send },
  { id: 'inbox', label: 'Inbox', icon: MessageSquare },
  { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { id: 'integrations', label: 'Integrations', icon: PlugZap },
  { id: 'calendar', label: 'Calendar', icon: Calendar },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const CollapsibleSidebar: React.FC<CollapsibleSidebarProps> = ({
  activeTab,
  onSelectTab,
  mobileOpen,
  onCloseMobile,
  onGoToHome,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  // Auto-expand sidebar when on any workspace view
  const [isPinned, setIsPinned] = useState(activeTab !== 'workspaces');

  // Auto-open sidebar when navigating to any console page
  React.useEffect(() => {
    if (activeTab !== 'workspaces') {
      setIsPinned(true);
    }
  }, [activeTab]);

  // Expanded if pinned OR currently hovered
  const isExpanded = isPinned || isHovered;

  const handleItemClick = (tabId: ConsoleTab) => {
    onSelectTab(tabId);
    onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop Blur Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-40 md:hidden animate-in fade-in"
          onClick={onCloseMobile}
        />
      )}

      {/* Main Sidebar Shell */}
      <aside
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={`
          fixed md:sticky top-0 md:top-[57px] left-0 z-40
          h-screen md:h-[calc(100vh-57px)]
          bg-white/90 backdrop-blur-xl border-r border-white/80
          shadow-lg md:shadow-[var(--shadow-glass)]
          sidebar-transition flex flex-col justify-between
          ${isExpanded ? 'w-64' : 'w-16'}
          ${mobileOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {/* Mobile Header (Close Button) */}
        <div className="flex md:hidden items-center justify-between p-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-[10px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-xs flex items-center justify-center border border-[var(--accent-border)]">
              SDR
            </div>
            <span className="text-xs font-bold text-[var(--text-primary)]">Codenter Navigation</span>
          </div>
          <button
            type="button"
            onClick={onCloseMobile}
            className="p-1.5 rounded-[10px] text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Top Navigation Items */}
        <div className="p-2.5 space-y-1 overflow-y-auto overflow-x-hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleItemClick(item.id)}
                title={!isExpanded ? item.label : undefined}
                className={`
                  w-full flex items-center gap-3.5 px-3 py-2.5 rounded-[16px] text-xs font-semibold
                  transition-all duration-150 group relative
                  ${
                    isActive
                      ? 'bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)] shadow-xs'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100/70'
                  }
                `}
              >
                {/* Icon Container */}
                <div
                  className={`w-5 h-5 flex items-center justify-center shrink-0 transition-transform ${
                    isActive ? 'scale-110' : 'group-hover:scale-105'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? 'text-[var(--accent-primary)]' : 'text-slate-400 group-hover:text-slate-600'
                    }`}
                  />
                </div>

                {/* Text Label (shown when expanded) */}
                {(isExpanded || mobileOpen) && (
                  <span className="truncate flex-1 text-left animate-in fade-in duration-150">
                    {item.label}
                  </span>
                )}

                {/* Optional Badge */}
                {(isExpanded || mobileOpen) && item.badge && (
                  <span
                    className={`px-1.5 py-0.5 rounded-[6px] text-[9px] font-black uppercase tracking-wider shrink-0 ${
                      isActive
                        ? 'bg-[var(--accent-primary)] text-white'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Bottom Utility Controls */}
        <div className="p-2.5 border-t border-slate-100/80 space-y-1">
          {/* Return to Home Page */}
          <button
            type="button"
            onClick={onGoToHome}
            title={!isExpanded ? 'Return to Home Page' : undefined}
            className="w-full flex items-center gap-3.5 px-3 py-2 rounded-[14px] text-xs font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-100/80 transition-all text-left group"
          >
            <Home className="w-4 h-4 text-slate-400 group-hover:text-slate-700 shrink-0" />
            {(isExpanded || mobileOpen) && (
              <span className="truncate animate-in fade-in duration-150">Return to Home</span>
            )}
          </button>

          {/* Desktop Pin / Collapse Lock */}
          <button
            type="button"
            onClick={() => setIsPinned(!isPinned)}
            className="hidden md:flex w-full items-center justify-between px-3 py-2 rounded-[14px] text-[11px] font-semibold text-slate-400 hover:text-slate-700 hover:bg-slate-100/80 transition-all cursor-pointer"
            title={isPinned ? 'Collapse Sidebar (Mini Icon Rail)' : 'Expand & Lock Sidebar Open'}
          >
            {isExpanded && (
              <span className="truncate">
                {isPinned ? 'Collapse Sidebar' : 'Lock Sidebar Open'}
              </span>
            )}
            <div className="w-5 h-5 flex items-center justify-center shrink-0 ml-auto">
              <Pin className={`w-3.5 h-3.5 ${isPinned ? 'text-[var(--accent-primary)] fill-[var(--accent-primary)]' : ''}`} />
            </div>
          </button>
        </div>
      </aside>
    </>
  );
};
