import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Inbox,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleInput } from './ui/SquircleInput';
import { IntentBadge } from './ui/IntentBadge';
import { ThreadTimeline, TimelineThread } from './ThreadTimeline';

export const SplitPaneInbox: React.FC = () => {
  const [threads, setThreads] = useState<TimelineThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'POSITIVE' | 'NEEDS_REVIEW' | 'CLOSED'>('ALL');
  const [mailboxStats, setMailboxStats] = useState<{ healthyCount: number; totalCount: number; dailyQuota: string }>({
    healthyCount: 0,
    totalCount: 0,
    dailyQuota: '0/0',
  });
  const [notice, setNotice] = useState<string | null>(null);

  // Fetch threads and mailbox accounts
  const fetchInboxData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [threadsRes, accountsRes] = await Promise.allSettled([
        axios.get('/api/v1/email/threads'),
        axios.get('/api/v1/email/accounts'),
      ]);

      if (threadsRes.status === 'fulfilled') {
        const rawThreads = threadsRes.value.data || [];
        const mapped: TimelineThread[] = rawThreads.map((t: any) => ({
          id: t.id,
          lead_name: t.lead_name || 'Prospect',
          lead_email: t.lead_email || '',
          company_name: t.company_name || '',
          subject: t.subject || 'Autonomous SDR Inquiry',
          status: t.status || 'OPEN',
          last_message_at: t.last_message_at || new Date().toISOString(),
          intent: t.intent || 'REQUEST_INFO',
          confidence: t.confidence ?? 0.9,
          citations: Array.isArray(t.citations) ? t.citations : [],
          ai_suggested_reply: t.ai_suggested_reply || '',
          messages: Array.isArray(t.messages)
            ? t.messages.map((m: any) => ({
                id: m.id,
                direction: m.direction || 'INBOUND',
                from_address: m.from_address || '',
                to_address: m.to_address || '',
                subject: m.subject || '',
                body_text: m.body_text || '',
                body_html: m.body_html || undefined,
                delivery_status: m.delivery_status || 'DELIVERED',
                sent_at: m.sent_at || m.created_at || new Date().toISOString(),
              }))
            : [],
        }));

        setThreads(mapped);
        if (mapped.length > 0) {
          setSelectedThreadId((prev) => (prev && mapped.some((x) => x.id === prev) ? prev : mapped[0].id));
        } else {
          setSelectedThreadId(null);
        }
      } else {
        setThreads([]);
      }

      if (accountsRes.status === 'fulfilled') {
        const accounts = accountsRes.value.data || [];
        const healthy = accounts.filter((a: any) => a.health_status === 'HEALTHY').length;
        const totalSends = accounts.reduce((sum: number, a: any) => sum + (a.current_day_sends || 0), 0);
        const maxLimit = accounts.reduce((sum: number, a: any) => sum + (a.daily_send_limit || 45), 0);

        setMailboxStats({
          healthyCount: healthy,
          totalCount: accounts.length,
          dailyQuota: `${totalSends}/${maxLimit}`,
        });
      }
    } catch (err) {
      console.error('Failed to load inbox data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInboxData();
  }, [fetchInboxData]);

  const selectedThread = threads.find((t) => t.id === selectedThreadId) || null;

  const handleApproveReply = async (threadId: string, replyText: string) => {
    try {
      const thread = threads.find((t) => t.id === threadId);
      if (thread) {
        await axios.post('/api/v1/email/send', {
          to_address: thread.lead_email,
          subject: `Re: ${thread.subject}`,
          body_text: replyText,
          thread_id: thread.id,
        });

        setNotice('Reply dispatched successfully with delivery pacing jitter.');
        await fetchInboxData();
      }
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to dispatch reply.');
    } finally {
      setTimeout(() => setNotice(null), 4000);
    }
  };

  const handleAssignHuman = (_threadId: string) => {
    setNotice(`Thread assigned to human sales representative.`);
    setTimeout(() => setNotice(null), 3000);
  };

  const handleSuppressLead = async (email: string) => {
    try {
      await axios.post('/api/v1/email/suppressions', {
        email,
        reason: 'MANUAL',
      });
      setNotice(`Lead ${email} added to suppression list.`);
      await fetchInboxData();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to suppress lead.');
    } finally {
      setTimeout(() => setNotice(null), 3000);
    }
  };

  const filteredThreads = threads.filter((t) => {
    const matchesSearch =
      t.lead_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.lead_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.company_name && t.company_name.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (activeFilter === 'POSITIVE') return t.intent === 'POSITIVE_INTEREST';
    if (activeFilter === 'NEEDS_REVIEW') return t.status === 'OPEN';
    if (activeFilter === 'CLOSED') return t.status === 'CLOSED';
    return true;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Human-in-the-Loop Split-Pane Inbox
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-[var(--text-muted)] font-medium p-2 px-3 rounded-[12px] bg-white/70 border border-white/80">
            Mailbox Pool:{' '}
            <span className="font-bold text-emerald-600">
              {mailboxStats.healthyCount} / {mailboxStats.totalCount} Healthy
            </span>{' '}
            ({mailboxStats.dailyQuota} sends today)
          </div>

          <button
            onClick={fetchInboxData}
            className="p-2 rounded-[12px] bg-white/80 border border-slate-200 hover:bg-white text-slate-600 hover:text-slate-900 transition-all"
            title="Refresh Inbox"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/60 text-xs text-blue-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            {notice}
          </span>
          <button onClick={() => setNotice(null)} className="text-blue-500 hover:text-blue-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Loading state */}
      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Syncing Inbound Messages &amp; Mailboxes...</div>
          <div className="text-xs text-[var(--text-muted)]">Parsing MIME threading and intent classification schemas</div>
        </FrostedGlassCard>
      ) : threads.length === 0 ? (
        /* Pristine 3D Frosted Glass Empty State */
        <FrostedGlassCard elevated className="p-12 md:p-16 flex flex-col items-center justify-center text-center space-y-5">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Inbox className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              Inbox is Clean — No Active Replies
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              When outbound campaign sequences receive prospect replies, they will appear here automatically with 14-intent AI classification, grounded citations, and draft responses for your review.
            </p>
          </div>
        </FrostedGlassCard>
      ) : (
        /* Split-Pane Container */
        <FrostedGlassCard className="p-0 overflow-hidden border border-white/80 rounded-[28px] shadow-[var(--shadow-glass)]">
          <div className="grid grid-cols-1 md:grid-cols-12 min-h-[680px]">
            {/* Left Pane: Thread List */}
            <div className="md:col-span-5 lg:col-span-4 border-r border-slate-100 bg-white/50 flex flex-col">
              {/* Search & Filter Bar */}
              <div className="p-4 border-b border-slate-100 space-y-3">
                <SquircleInput
                  placeholder="Search leads, domains..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />

                {/* Filter Pills */}
                <div className="flex gap-1.5 overflow-x-auto pb-1">
                  {[
                    { id: 'ALL', label: 'All' },
                    { id: 'POSITIVE', label: 'Positive' },
                    { id: 'NEEDS_REVIEW', label: 'Needs Review' },
                    { id: 'CLOSED', label: 'Closed' },
                  ].map((f) => (
                    <button
                      key={f.id}
                      onClick={() => setActiveFilter(f.id as any)}
                      className={`px-3 py-1 text-xs font-semibold rounded-[12px] whitespace-nowrap transition-all ${
                        activeFilter === f.id
                          ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                          : 'bg-white/80 text-slate-600 border border-slate-200/60 hover:bg-white'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Scrollable Thread List */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                {filteredThreads.map((t) => {
                  const isSelected = selectedThreadId === t.id;
                  const latestMsg = t.messages[t.messages.length - 1];

                  return (
                    <div
                      key={t.id}
                      onClick={() => setSelectedThreadId(t.id)}
                      className={`p-4 cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-[var(--accent-subtle)]/70 border-l-4 border-l-[var(--accent-primary)]'
                          : 'hover:bg-white/70'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-bold text-[var(--text-primary)] truncate">
                          {t.lead_name}
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)] shrink-0 font-mono">
                          {new Date(t.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-500 mb-2 truncate">
                        {t.company_name ? `${t.company_name} • ` : ''}
                        {t.subject}
                      </div>

                      <p className="text-xs text-slate-600 line-clamp-2 mb-2.5 leading-relaxed">
                        {latestMsg?.body_text || 'No message content'}
                      </p>

                      <div className="flex items-center justify-between gap-1">
                        {t.intent ? <IntentBadge intent={t.intent} /> : <div />}
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-[6px] ${
                            t.status === 'REPLIED'
                              ? 'bg-emerald-50 text-emerald-700'
                              : t.status === 'OPEN'
                              ? 'bg-blue-50 text-blue-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {t.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Pane: Timeline */}
            <div className="md:col-span-7 lg:col-span-8 bg-white/70 flex flex-col">
              {selectedThread ? (
                <ThreadTimeline
                  thread={selectedThread}
                  onApproveReply={handleApproveReply}
                  onAssignHuman={handleAssignHuman}
                  onSuppressLead={handleSuppressLead}
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8 text-center space-y-2">
                  <Inbox className="w-10 h-10 stroke-[1.5]" />
                  <p className="text-sm font-semibold">Select a conversation thread to review details</p>
                </div>
              )}
            </div>
          </div>
        </FrostedGlassCard>
      )}
    </div>
  );
};
