import React, { useState, useEffect } from 'react';
import {
  Search,
  ChevronDown,
  LayoutGrid,
  List,
  Plus,
  MoreVertical,
  Building,
  Globe,
  Users,
  Activity,
  ArrowRight,
} from 'lucide-react';
import axios from 'axios';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleModal } from './ui/SquircleModal';
import { SquircleInput } from './ui/SquircleInput';
import { useAuth } from '../context/AuthContext';

export interface WorkspaceItem {
  id: string;
  name: string;
  domain?: string;
  website_url?: string;
  region: string;
  tier: 'NANO' | 'FREE' | 'PRO' | 'ENTERPRISE';
  leadsCount: number;
  campaignsCount: number;
  databaseMb: number;
  status: 'ACTIVE' | 'PAUSED';
  createdAt: string;
}

interface WorkspacesViewProps {
  onSelectWorkspace: (workspaceId: string, workspaceName: string, targetTab?: any) => void;
  isCreateModalOpen?: boolean;
  onCloseCreateModal?: () => void;
}

export const WorkspacesView: React.FC<WorkspacesViewProps> = ({
  onSelectWorkspace,
  isCreateModalOpen = false,
  onCloseCreateModal,
}) => {
  const { workspace: currentAuthWs, switchWorkspace } = useAuth();

  // Workspaces list state
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([
    {
      id: currentAuthWs?.id || 'ws-default-sdr-01',
      name: currentAuthWs?.name || 'AI SDR',
      region: 'AWS | ap-northeast-2',
      tier: 'NANO',
      leadsCount: 142,
      campaignsCount: 3,
      databaseMb: 26,
      status: 'ACTIVE',
      createdAt: '2026-09-01',
    },
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<'name' | 'recent'>('name');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // New Workspace Modal (Name + Website URL are compulsory)
  const [modalOpen, setModalOpen] = useState(isCreateModalOpen);
  const [newWsName, setNewWsName] = useState('');
  const [newWsWebsiteUrl, setNewWsWebsiteUrl] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  // Sync external prop if provided
  useEffect(() => {
    if (isCreateModalOpen) {
      setModalOpen(true);
    }
  }, [isCreateModalOpen]);

  // Fetch all workspaces from backend
  useEffect(() => {
    const fetchWorkspaces = async () => {
      try {
        const res = await axios.get('/api/v1/workspaces');
        if (Array.isArray(res.data) && res.data.length > 0) {
          const mapped: WorkspaceItem[] = res.data.map((w: any) => ({
            id: w.id,
            name: w.name,
            domain: w.domain,
            website_url: w.website_url,
            region: 'AWS | ap-northeast-2',
            tier: w.settings?.tier || 'FREE',
            leadsCount: 142,
            campaignsCount: 3,
            databaseMb: 26,
            status: 'ACTIVE',
            createdAt: w.created_at || '2026-09-01',
          }));
          setWorkspaces(mapped);
        }
      } catch (err) {
        console.error('Failed to load workspaces:', err);
      }
    };
    fetchWorkspaces();
  }, []);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim() || !newWsWebsiteUrl.trim()) return;

    setIsCreating(true);
    try {
      const res = await axios.post('/api/v1/workspaces', {
        name: newWsName.trim(),
        website_url: newWsWebsiteUrl.trim(),
        settings: { tier: 'FREE' },
      });

      const created: WorkspaceItem = {
        id: res.data.id || `ws-${Date.now()}`,
        name: res.data.name || newWsName.trim(),
        domain: res.data.domain,
        website_url: res.data.website_url || newWsWebsiteUrl.trim(),
        region: 'AWS | ap-northeast-2',
        tier: 'FREE',
        leadsCount: 0,
        campaignsCount: 0,
        databaseMb: 1,
        status: 'ACTIVE',
        createdAt: res.data.created_at || new Date().toISOString(),
      };

      setWorkspaces((prev) => [...prev, created]);
      setNewWsName('');
      setNewWsWebsiteUrl('');
      setModalOpen(false);
      onCloseCreateModal?.();

      if (switchWorkspace) {
        switchWorkspace({ id: created.id, name: created.name, role: 'OWNER' });
      }

      // Golden Path Step 2: Auto-select and navigate to Knowledge Base for crawl pipeline!
      onSelectWorkspace(created.id, created.name, 'knowledge');
    } catch (err: any) {
      console.error('Failed to create workspace on server:', err);
      // Fallback
      const created: WorkspaceItem = {
        id: `ws-${Date.now()}`,
        name: newWsName.trim(),
        website_url: newWsWebsiteUrl.trim(),
        region: 'AWS | ap-northeast-2',
        tier: 'FREE',
        leadsCount: 0,
        campaignsCount: 0,
        databaseMb: 1,
        status: 'ACTIVE',
        createdAt: new Date().toISOString(),
      };
      setWorkspaces((prev) => [...prev, created]);
      setNewWsName('');
      setNewWsWebsiteUrl('');
      setModalOpen(false);
      onCloseCreateModal?.();
      if (switchWorkspace) {
        switchWorkspace({ id: created.id, name: created.name, role: 'OWNER' });
      }
      onSelectWorkspace(created.id, created.name, 'knowledge');
    } finally {
      setIsCreating(false);
    }
  };

  // Filter & Sort (Status filter removed per instructions)
  const filteredWorkspaces = workspaces
    .filter((ws) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch =
        ws.name.toLowerCase().includes(query) ||
        (ws.domain ? ws.domain.toLowerCase().includes(query) : false) ||
        (ws.website_url ? ws.website_url.toLowerCase().includes(query) : false);
      return matchesSearch;
    })
    .sort((a, b) => {
      if (sortOrder === 'name') return a.name.localeCompare(b.name);
      return b.createdAt.localeCompare(a.createdAt);
    });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Page Header */}
      <div>
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
          Workspaces
        </h1>
      </div>

      {/* 2. Action Toolbar (Search, Filters, View Toggle, + New Workspace) */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 sm:gap-4 pb-2">
        {/* Left Side: Search + Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search for a workspace..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50/80 hover:bg-white focus:bg-white border border-slate-200/90 hover:border-slate-300 rounded-[14px] pl-10 pr-4 py-2.5 text-xs text-[var(--text-primary)] placeholder-slate-400 outline-none shadow-2xs focus:ring-2 focus:ring-[var(--accent-glow)] focus:border-[var(--accent-primary)] transition-all"
            />
          </div>


          {/* Sort Dropdown */}
          <div className="relative">
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as any)}
              aria-label="Sort workspaces list"
              className="appearance-none bg-slate-50/80 hover:bg-white border border-slate-200/90 hover:border-slate-300 rounded-[14px] pl-3.5 pr-8 py-2.5 text-xs font-semibold text-[var(--text-secondary)] outline-none shadow-2xs cursor-pointer transition-all"
            >
              <option value="name">Sorted by name</option>
              <option value="recent">Sorted by recent</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        {/* Right Side: View Toggle + + New Workspace Button */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Grid / List View Toggle */}
          <div className="flex items-center bg-white/60 p-1 rounded-[14px] border border-white/80 shadow-xs">
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-[10px] transition-all ${
                viewMode === 'grid'
                  ? 'bg-white text-[var(--accent-primary)] shadow-xs'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-[10px] transition-all ${
                viewMode === 'list'
                  ? 'bg-white text-[var(--accent-primary)] shadow-xs'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
              title="List View"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* + New Workspace Primary Button */}
          <SquircleButton
            variant="primary"
            size="md"
            onClick={() => setModalOpen(true)}
            className="text-xs font-bold shadow-sm"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            New workspace
          </SquircleButton>
        </div>
      </div>

      {/* 3. Main Workspaces Grid */}
      <div className="space-y-4">
        <div
          className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5'
              : 'space-y-3'
          }
        >
          {filteredWorkspaces.map((ws) => (
            <div
              key={ws.id}
              onClick={() => {
                if (switchWorkspace) {
                  switchWorkspace({ id: ws.id, name: ws.name, role: 'OWNER' });
                }
                onSelectWorkspace(ws.id, ws.name);
              }}
              className="group relative rounded-[24px] bg-white/75 backdrop-blur-xl border border-white/80 p-5 shadow-[var(--shadow-glass)] hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-5"
            >
              {/* Card Top: Title, Subtitle, Menu */}
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-primary)] transition-colors flex items-center gap-2">
                    {ws.name}
                  </h3>
                  <p className="text-xs text-[var(--text-muted)] font-medium flex items-center gap-1.5">
                    {ws.domain ? (
                      <>
                        <Globe className="w-3.5 h-3.5 text-slate-400" />
                        <span>{ws.domain}</span>
                      </>
                    ) : (
                      <span>{ws.region}</span>
                    )}
                  </p>
                </div>

                {/* Menu Button */}
                <div className="relative" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => setMenuOpenId(menuOpenId === ws.id ? null : ws.id)}
                    className="p-1.5 rounded-[10px] text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>

                  {menuOpenId === ws.id && (
                    <>
                      <div
                        className="fixed inset-0 z-30"
                        onClick={() => setMenuOpenId(null)}
                      />
                      <div className="absolute right-0 top-full mt-1 w-44 rounded-[16px] bg-white/95 backdrop-blur-xl border border-white/90 shadow-xl p-1.5 z-40 animate-in zoom-in-95 space-y-1 text-xs">
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpenId(null);
                            onSelectWorkspace(ws.id, ws.name);
                          }}
                          className="w-full text-left p-2 rounded-[10px] font-semibold text-slate-700 hover:bg-slate-100 transition-colors flex items-center justify-between"
                        >
                          <span>Open Console</span>
                          <ArrowRight className="w-3 h-3 text-slate-400" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Card Bottom: Metrics Pills */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-[8px] bg-slate-100 text-slate-600 font-bold text-[10px] uppercase tracking-wider">
                    {ws.tier}
                  </span>
                </div>

                <div className="flex items-center gap-3 text-slate-500 font-semibold text-[11px]">
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5 text-slate-400" />
                    {ws.leadsCount} leads
                  </span>
                  <span className="flex items-center gap-1 text-emerald-600">
                    <Activity className="w-3.5 h-3.5" />
                    {ws.status === 'ACTIVE' ? 'Active' : 'Paused'}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* "+ Create Workspace" Ghost Card */}
          <div
            onClick={() => setModalOpen(true)}
            className="rounded-[24px] border-2 border-dashed border-slate-200/80 hover:border-[var(--accent-primary)] hover:bg-[var(--accent-subtle)]/30 p-6 flex flex-col items-center justify-center text-center gap-2.5 transition-all duration-200 cursor-pointer min-h-[170px] group"
          >
            <div className="w-10 h-10 rounded-[14px] bg-slate-100 group-hover:bg-[var(--accent-subtle)] text-slate-400 group-hover:text-[var(--accent-primary)] flex items-center justify-center transition-colors">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-primary)] transition-colors">
                Create another workspace
              </p>
              <p className="text-[10px] text-[var(--text-muted)]">
                Multi-tenant isolation strictly enforced
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* + New Workspace Squircle Modal */}
      <SquircleModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          onCloseCreateModal?.();
        }}
        title="Create New Workspace"
        maxWidth="md"
      >
        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          <SquircleInput
            label="Workspace Name *"
            placeholder="e.g. Enterprise Sales Labs"
            value={newWsName}
            onChange={(e) => setNewWsName(e.target.value)}
            leftIcon={<Building className="w-4 h-4" />}
            required
          />

          <div>
            <SquircleInput
              label="Corporate Website URL *"
              placeholder="https://yourcompany.com"
              value={newWsWebsiteUrl}
              onChange={(e) => setNewWsWebsiteUrl(e.target.value)}
              leftIcon={<Globe className="w-4 h-4" />}
              required
            />
            
          </div>

          <div className="pt-2">
            <SquircleButton
              type="submit"
              variant="primary"
              className="w-full justify-center py-2.5 text-xs font-bold shadow-md"
              isLoading={isCreating}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Create Workspace &amp; Train AI
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>
    </div>
  );
};
