import React, { useState } from 'react';
import {
  Menu,
  Search,
  HelpCircle,
  MessageSquare,
  ChevronDown,
  Building,
  Check,
  Plus,
  ArrowLeft,
  LogOut,
  Sliders
} from 'lucide-react';
import { ThemePicker } from './ThemePicker';
import { useAuth } from '../../context/AuthContext';

interface ConsoleHeaderProps {
  onToggleMobileSidebar: () => void;
  onGoToHome: () => void;
  onNavigateTab: (tab: string) => void;
  activeWorkspaceName?: string;
  onOpenNewWorkspaceModal: () => void;
}

export const ConsoleHeader: React.FC<ConsoleHeaderProps> = ({
  onToggleMobileSidebar,
  onGoToHome,
  onNavigateTab,
  activeWorkspaceName,
  onOpenNewWorkspaceModal,
}) => {
  const { user, workspace, logout } = useAuth();
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const currentWsName = activeWorkspaceName || workspace?.name || 'AI SDR';

  return (
    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-white/80 shadow-[var(--shadow-glass)] px-4 sm:px-6 py-2.5 transition-all">
      <div className="flex items-center justify-between gap-2 sm:gap-4">
        {/* Left Side: Hamburger (Mobile) + Logo + Slash + Workspace Selector */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Mobile Hamburger Toggle */}
          <button
            type="button"
            onClick={onToggleMobileSidebar}
            className="md:hidden p-2 rounded-[12px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100 transition-colors"
            title="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Logo Mark */}
          <div
            onClick={onGoToHome}
            className="flex items-center gap-2 cursor-pointer group"
            title="Return to Home Page"
          >
            <div className="w-8 h-8 rounded-[12px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-xs flex items-center justify-center border border-[var(--accent-border)] shadow-xs group-hover:scale-105 transition-transform">
              SDR
            </div>
          </div>

          {/* Slash Divider */}
          <span className="text-slate-300 font-light text-lg select-none">/</span>

          {/* Workspace Selector Dropdown Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setWorkspaceDropdownOpen(!workspaceDropdownOpen)}
              className="flex items-center gap-2 py-1.5 px-2.5 rounded-[14px] bg-white/60 hover:bg-white border border-slate-200/80 shadow-xs hover:shadow-sm text-xs font-semibold text-[var(--text-primary)] transition-all"
            >
              <div className="w-5 h-5 rounded-[8px] bg-slate-100 text-slate-700 flex items-center justify-center">
                <Building className="w-3 h-3" />
              </div>
              <span className="truncate max-w-[120px] sm:max-w-[160px]">
                {currentWsName}
              </span>
              <span className="px-1.5 py-0.2 rounded-[6px] bg-emerald-100/90 text-emerald-800 text-[9px] font-black border border-emerald-200">
                FREE
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {/* Workspace Switcher Popover */}
            {workspaceDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setWorkspaceDropdownOpen(false)}
                />
                <div className="absolute left-0 top-full mt-1.5 w-64 rounded-[20px] bg-white/95 backdrop-blur-xl border border-white/90 shadow-xl p-2 z-50 animate-in zoom-in-95 space-y-1">
                  <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Active Workspace
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-[12px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] text-xs font-bold text-[var(--accent-primary)]">
                    <div className="flex items-center gap-2">
                      <Building className="w-3.5 h-3.5" />
                      <span>{currentWsName}</span>
                    </div>
                    <Check className="w-3.5 h-3.5" />
                  </div>

                  <div className="pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => {
                        setWorkspaceDropdownOpen(false);
                        onNavigateTab('workspaces');
                      }}
                      className="w-full flex items-center gap-2 p-2 rounded-[12px] text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all text-left"
                    >
                      <Sliders className="w-3.5 h-3.5" />
                      <span>Manage All Workspaces</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setWorkspaceDropdownOpen(false);
                        onOpenNewWorkspaceModal();
                      }}
                      className="w-full flex items-center gap-2 p-2 rounded-[12px] text-xs font-bold text-[var(--accent-primary)] hover:bg-[var(--accent-subtle)] transition-all text-left"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>+ Create New Workspace</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Center / Right Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick Search Bar (Ctrl + K) */}
          <div className="hidden lg:flex items-center relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 pointer-events-none" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-48 xl:w-64 bg-slate-100/80 hover:bg-slate-100 focus:bg-white border border-slate-200/80 rounded-[14px] pl-9 pr-14 py-1.5 text-xs text-[var(--text-primary)] placeholder-slate-400 outline-none transition-all focus:ring-2 focus:ring-[var(--accent-glow)]"
            />
            <span className="absolute right-2.5 px-1.5 py-0.5 rounded-[6px] bg-white border border-slate-200 text-[10px] font-bold text-slate-400 pointer-events-none shadow-2xs">
              Ctrl K
            </span>
          </div>

          {/* Feedback Button */}
          <button
            type="button"
            onClick={() => alert('Feedback submitted! Thank you for testing Codenter AI SDR.')}
            className="hidden sm:flex items-center gap-1.5 py-1.5 px-2.5 rounded-[12px] text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
            <span>Feedback</span>
          </button>

          {/* Help Icon */}
          <button
            type="button"
            onClick={() => window.open('https://github.com/UmarAjmal/AI-SDR', '_blank')}
            title="Documentation & Guides"
            className="p-2 rounded-[12px] text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          {/* Dynamic ThemePicker */}
          <ThemePicker />

          {/* User Avatar Circle with Menu */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="w-8 h-8 rounded-[12px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-bold text-xs flex items-center justify-center border border-[var(--accent-border)] hover:ring-2 hover:ring-[var(--accent-glow)] transition-all shadow-xs"
              title={`Logged in as ${user?.email}`}
            >
              {user?.email ? user.email.charAt(0).toUpperCase() : 'U'}
            </button>

            {/* User Dropdown Menu */}
            {userDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setUserDropdownOpen(false)}
                />
                <div className="absolute right-0 top-full mt-1.5 w-56 rounded-[20px] bg-white/95 backdrop-blur-xl border border-white/90 shadow-xl p-2 z-50 animate-in zoom-in-95 space-y-1">
                  <div className="px-3 py-2 border-b border-slate-100">
                    <p className="text-xs font-bold text-[var(--text-primary)] truncate">
                      {user?.email}
                    </p>
                    <p className="text-[10px] text-slate-400 font-medium">
                      Role: {workspace?.role || 'OWNER'}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setUserDropdownOpen(false);
                      onGoToHome();
                    }}
                    className="w-full flex items-center gap-2 p-2 rounded-[12px] text-xs font-medium text-slate-700 hover:bg-slate-100 transition-all text-left"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Return to Home Page</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUserDropdownOpen(false);
                      onNavigateTab('settings');
                    }}
                    className="w-full flex items-center gap-2 p-2 rounded-[12px] text-xs font-medium text-slate-700 hover:bg-slate-100 transition-all text-left"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Workspace Settings</span>
                  </button>

                  <div className="pt-1 border-t border-slate-100">
                    <button
                      type="button"
                      onClick={() => {
                        setUserDropdownOpen(false);
                        logout();
                        onGoToHome();
                      }}
                      className="w-full flex items-center gap-2 p-2 rounded-[12px] text-xs font-bold text-rose-600 hover:bg-rose-50 transition-all text-left"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
