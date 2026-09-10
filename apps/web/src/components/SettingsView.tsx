import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Shield,
  DollarSign,
  Mail,
  Users,
  Save,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput, SquircleTextarea } from './ui/SquircleInput';

export const SettingsView: React.FC = () => {
  const [workspaceId, setWorkspaceId] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [domain, setDomain] = useState('');
  const [spendingLimit, setSpendingLimit] = useState(100.0);
  const [dailySendLimit, setDailySendLimit] = useState(45);
  const [minJitterSecs, setMinJitterSecs] = useState(120);
  const [maxJitterSecs, setMaxJitterSecs] = useState(300);
  const [prohibitedClaims, setProhibitedClaims] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Fetch active workspace settings
  useEffect(() => {
    const fetchWorkspace = async () => {
      setIsLoading(true);
      try {
        const res = await axios.get('/api/v1/workspaces/current');
        if (res.data) {
          const w = res.data;
          setWorkspaceId(w.id || '');
          setWorkspaceName(w.name || '');
          setDomain(w.domain || '');

          const s = w.settings || {};
          if (s.spending_limit_usd !== undefined) setSpendingLimit(Number(s.spending_limit_usd));
          if (s.daily_send_limit !== undefined) setDailySendLimit(Number(s.daily_send_limit));
          if (s.min_jitter_secs !== undefined) setMinJitterSecs(Number(s.min_jitter_secs));
          if (s.max_jitter_secs !== undefined) setMaxJitterSecs(Number(s.max_jitter_secs));
          if (s.prohibited_claims !== undefined) setProhibitedClaims(String(s.prohibited_claims));
        }
      } catch (err) {
        console.error('Failed to load workspace settings:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchWorkspace();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await axios.put('/api/v1/workspaces/current', {
        name: workspaceName.trim(),
        domain: domain.trim(),
        settings: {
          spending_limit_usd: spendingLimit,
          daily_send_limit: dailySendLimit,
          min_jitter_secs: minJitterSecs,
          max_jitter_secs: maxJitterSecs,
          prohibited_claims: prohibitedClaims,
        },
      });

      setNotice('Workspace settings and compliance guardrails successfully persisted in PostgreSQL!');
      setTimeout(() => setNotice(null), 4000);
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to save settings.');
      setTimeout(() => setNotice(null), 4000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Workspace Governance &amp; Safeguards
          </h2>
        </div>

        <SquircleButton
          variant="primary"
          size="sm"
          onClick={handleSave}
          isLoading={isSaving}
          className="flex items-center gap-1.5 self-start shadow-sm"
        >
          <Save className="w-3.5 h-3.5" />
          Save Settings
        </SquircleButton>
      </div>

      {/* Notice Banner */}
      {notice && (
        <FrostedGlassCard className="p-3.5 border-emerald-200/80 bg-emerald-50/60 text-xs text-emerald-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {notice}
          </span>
          <button onClick={() => setNotice(null)} className="text-emerald-500 hover:text-emerald-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Loading Workspace Profile...</div>
          <div className="text-xs text-[var(--text-muted)]">Verifying tenant isolation claims</div>
        </FrostedGlassCard>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Card 1: Workspace Profile & Multi-Tenant ID */}
          <FrostedGlassCard className="p-6 md:p-8 space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Users className="w-4 h-4 text-[var(--accent-primary)]" />
              Workspace Organization
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Canonical tenant boundaries strictly isolated via JWT workspace claims.
            </p>

            <div className="space-y-4 pt-2">
              <SquircleInput
                label="Organization Name"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder="Your Company Name"
              />
              <SquircleInput
                label="Primary Company Domain"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="yourcompany.com"
              />
              <div className="p-3 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-700">
                <span className="font-semibold text-slate-500">Authenticated Tenant ID: </span>
                <span className="font-mono text-[11px] text-[var(--accent-primary)] font-bold">
                  {workspaceId || 'current-workspace'}
                </span>
              </div>
            </div>
          </FrostedGlassCard>

          {/* Card 2: Spending Limit & Token Quotas */}
          <FrostedGlassCard className="p-6 md:p-8 space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              Monthly Spending Cap &amp; Metering
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Section 19 safety guard: automatically pauses active campaigns if monthly spend exceeds limit.
            </p>

            <div className="space-y-4 pt-2">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
                  Monthly Budget Cap (USD)
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-bold text-slate-400">
                    $
                  </span>
                  <input
                    type="number"
                    value={spendingLimit}
                    onChange={(e) => setSpendingLimit(parseFloat(e.target.value) || 0)}
                    className="w-full bg-white/70 backdrop-blur-md border border-slate-200/80 rounded-[16px] pl-8 pr-4 py-3 text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[var(--accent-glow)]"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-[16px] bg-emerald-50/70 border border-emerald-200/80 text-xs text-emerald-800 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Budget Overrun Protection Active
                </div>
                <p className="text-[11px] leading-relaxed text-emerald-700">
                  When 100% of the monthly budget is consumed, all running outbound Celery worker queues halt immediately.
                </p>
              </div>
            </div>
          </FrostedGlassCard>

          {/* Card 3: Anti-Spam Jitter & Deliverability Caps */}
          <FrostedGlassCard className="p-6 md:p-8 space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Mail className="w-4 h-4 text-blue-600" />
              Deliverability Caps &amp; Pacing Jitter
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Section 11.3: Anti-spam randomized delays between outbound email dispatches to preserve inbox reputation.
            </p>

            <div className="space-y-4 pt-2">
              <SquircleInput
                label="Per-Mailbox Daily Send Limit (30–50 cold emails/day)"
                type="number"
                value={dailySendLimit}
                onChange={(e) => setDailySendLimit(parseInt(e.target.value, 10) || 30)}
              />

              <div className="grid grid-cols-2 gap-3">
                <SquircleInput
                  label="Min Jitter Delay (seconds)"
                  type="number"
                  value={minJitterSecs}
                  onChange={(e) => setMinJitterSecs(parseInt(e.target.value, 10) || 120)}
                />
                <SquircleInput
                  label="Max Jitter Delay (seconds)"
                  type="number"
                  value={maxJitterSecs}
                  onChange={(e) => setMaxJitterSecs(parseInt(e.target.value, 10) || 300)}
                />
              </div>

              <p className="text-[11px] text-[var(--text-muted)]">
                Randomized interval between <span className="font-bold text-slate-700">{minJitterSecs}s</span> and{' '}
                <span className="font-bold text-slate-700">{maxJitterSecs}s</span> prevents ESP rate-limiting and domain burning.
              </p>
            </div>
          </FrostedGlassCard>

          {/* Card 4: Prohibited AI Claims Policy */}
          <FrostedGlassCard className="p-6 md:p-8 space-y-4">
            <h3 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-600" />
              Prohibited AI Claims &amp; Anti-Hallucination Policy
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Section 7.3: Outbound AI generation filter blocks ungrounded claims before dispatching.
            </p>

            <div className="space-y-2 pt-2">
              <SquircleTextarea
                rows={5}
                value={prohibitedClaims}
                onChange={(e) => setProhibitedClaims(e.target.value)}
                placeholder="Enter prohibited claims, e.g. Never promise discounts exceeding 20% without human approval..."
              />
              <p className="text-[11px] text-[var(--text-muted)]">
                The Model Gateway validates all generated drafts against this policy. If a violation is detected, generation is regenerated or routed to human review.
              </p>
            </div>
          </FrostedGlassCard>
        </div>
      )}
    </div>
  );
};
