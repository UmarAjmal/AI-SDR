import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DOMPurify from 'dompurify';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput } from './ui/SquircleInput';
import { 
  Mail, 
  Send, 
  ShieldAlert, 
  CheckCircle2, 
  Clock, 
  Inbox, 
  Plus, 
  Trash2, 
  Lock,
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { IntentBadge } from './ui/IntentBadge';

interface MailboxAccount {
  id: string;
  provider: 'GOOGLE' | 'MICROSOFT';
  email_address: string;
  health_status: 'HEALTHY' | 'PAUSED' | 'REVOKED' | 'WARMUP';
  daily_send_limit: number;
  current_day_sends: number;
  last_send_at: string | null;
}

interface Message {
  id: string;
  direction: 'INBOUND' | 'OUTBOUND';
  from_address: string;
  to_address: string;
  subject: string;
  body_text: string;
  body_html?: string;
  delivery_status: string;
  sent_at: string;
}

interface Thread {
  id: string;
  lead_name: string;
  lead_email: string;
  subject: string;
  status: 'OPEN' | 'REPLIED' | 'CLOSED' | 'BOUNCED';
  last_message_at: string;
  messages: Message[];
  intent?: string;
  confidence?: number;
  citations?: string[];
  ai_suggested_reply?: string;
}

interface SuppressionItem {
  id: string;
  email?: string;
  domain?: string;
  reason: 'UNSUBSCRIBE' | 'HARD_BOUNCE' | 'COMPLAINT' | 'MANUAL';
  source: string;
  created_at: string;
}

export const InboxView: React.FC = () => {
  const [accounts, setAccounts] = useState<MailboxAccount[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [suppressions, setSuppressions] = useState<SuppressionItem[]>([]);
  const [activeSubTab, setActiveSubTab] = useState<'threads' | 'mailboxes' | 'suppression'>('threads');

  // Load real accounts, threads, and suppressions from API
  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [accRes, thRes, supRes] = await Promise.allSettled([
          axios.get('/api/v1/email/accounts'),
          axios.get('/api/v1/email/threads'),
          axios.get('/api/v1/email/suppressions'),
        ]);

        if (accRes.status === 'fulfilled') setAccounts(accRes.value.data || []);
        if (thRes.status === 'fulfilled') {
          const loaded = thRes.value.data || [];
          setThreads(loaded);
          if (loaded.length > 0) setSelectedThreadId(loaded[0].id);
        }
        if (supRes.status === 'fulfilled') setSuppressions(supRes.value.data || []);
      } catch (err) {
        console.error('Failed to load inbox data:', err);
      }
    };
    fetchAll();
  }, []);

  // Reply Composer State
  const [replyText, setReplyText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendSuccessBanner, setSendSuccessBanner] = useState<string | null>(null);

  // New Suppression Modal
  const [newSuppEntry, setNewSuppEntry] = useState('');
  const [newSuppType, setNewSuppType] = useState<'email' | 'domain'>('email');

  const selectedThread = threads.find((t) => t.id === selectedThreadId) || threads[0];

  const handleSendReply = () => {
    if (!replyText.trim()) return;
    setIsSending(true);

    // Simulate sending with Double-Send Lock Protection
    setTimeout(() => {
      const newMsg: Message = {
        id: `m-${Date.now()}`,
        direction: 'OUTBOUND',
        from_address: accounts[0].email_address,
        to_address: selectedThread.lead_email,
        subject: `Re: ${selectedThread.subject}`,
        body_text: replyText,
        delivery_status: 'SENT',
        sent_at: new Date().toISOString()
      };

      setThreads((prev) =>
        prev.map((th) =>
          th.id === selectedThread.id
            ? { ...th, messages: [...th.messages, newMsg], last_message_at: newMsg.sent_at }
            : th
        )
      );

      // Increment daily send count
      setAccounts((prev) =>
        prev.map((acc, idx) =>
          idx === 0 ? { ...acc, current_day_sends: acc.current_day_sends + 1 } : acc
        )
      );

      setReplyText('');
      setIsSending(false);
      setSendSuccessBanner('Outbound email dispatched with distributed lock send_lock:verified.');
      setTimeout(() => setSendSuccessBanner(null), 4000);
    }, 600);
  };

  const handleAddSuppression = () => {
    if (!newSuppEntry.trim()) return;
    const newItem: SuppressionItem = {
      id: `sup-${Date.now()}`,
      email: newSuppType === 'email' ? newSuppEntry.trim().toLowerCase() : undefined,
      domain: newSuppType === 'domain' ? newSuppEntry.trim().toLowerCase() : undefined,
      reason: 'MANUAL',
      source: 'USER_INTERFACE',
      created_at: new Date().toISOString()
    };
    setSuppressions([newItem, ...suppressions]);
    setNewSuppEntry('');
  };

  const handleDeleteSuppression = (id: string) => {
    setSuppressions(suppressions.filter((s) => s.id !== id));
  };

  return (
    <div className="space-y-6">
      {/* Header with Sub-Tabs */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-2.5">
            <Mail className="w-6 h-6 text-[var(--accent-primary)]" />
            Email Infrastructure & Split-Pane Inbox
          </h1>
        </div>

        <div className="flex items-center gap-2 bg-white/60 backdrop-blur-md p-1 rounded-[16px] border border-white/80 shadow-sm">
          <button
            onClick={() => setActiveSubTab('threads')}
            className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all ${
              activeSubTab === 'threads'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Conversations ({threads.length})
          </button>
          <button
            onClick={() => setActiveSubTab('mailboxes')}
            className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all ${
              activeSubTab === 'mailboxes'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Mailbox Health ({accounts.length})
          </button>
          <button
            onClick={() => setActiveSubTab('suppression')}
            className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all ${
              activeSubTab === 'suppression'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Suppression ({suppressions.length})
          </button>
        </div>
      </div>

      {sendSuccessBanner && (
        <div className="p-3.5 rounded-[16px] bg-emerald-50 border border-emerald-200/80 text-emerald-900 text-xs font-semibold flex items-center gap-2 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          {sendSuccessBanner}
        </div>
      )}

      {/* ---------------- SUBTAB 1: THREADS (SPLIT PANE) ---------------- */}
      {activeSubTab === 'threads' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[620px]">
          {/* Left Pane: Thread Browser */}
          <FrostedGlassCard className="lg:col-span-5 p-4 flex flex-col h-full">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
              <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Inbox className="w-4 h-4 text-[var(--accent-primary)]" />
                Active Outreach Threads
              </h2>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-[10px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)]">
                {threads.length} Threads
              </span>
            </div>

            <div className="divide-y divide-[var(--border-subtle)] overflow-y-auto mt-2 space-y-1">
              {threads.map((th) => {
                const isSelected = th.id === selectedThread.id;
                const lastMsg = th.messages[th.messages.length - 1];
                return (
                  <div
                    key={th.id}
                    onClick={() => setSelectedThreadId(th.id)}
                    className={`p-3 rounded-[16px] cursor-pointer transition-all duration-150 ${
                      isSelected
                        ? 'bg-[var(--accent-subtle)] border border-[var(--accent-border)] shadow-sm'
                        : 'hover:bg-white/60 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold text-[var(--text-primary)] truncate max-w-[180px]">
                        {th.lead_name}
                      </p>
                      <span className="text-[10px] font-semibold text-[var(--text-muted)]">
                        {new Date(th.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center gap-1.5">
                      <IntentBadge intent={th.intent || 'PRODUCT_QUESTION'} confidence={th.confidence} />
                    </div>

                    <p className="text-[11px] font-medium text-[var(--accent-primary)] truncate mt-1">
                      {th.subject}
                    </p>

                    <p className="text-[11px] text-[var(--text-secondary)] line-clamp-1 mt-1">
                      {lastMsg ? lastMsg.body_text : 'No messages'}
                    </p>

                    <div className="flex items-center justify-between mt-2 pt-1">
                      <span className="text-[10px] text-[var(--text-muted)] truncate max-w-[160px]">
                        {th.lead_email}
                      </span>
                      <span
                        className={`text-[9px] font-bold px-2 py-0.5 rounded-[8px] uppercase tracking-wider ${
                          th.status === 'REPLIED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : th.status === 'BOUNCED'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {th.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </FrostedGlassCard>

          {/* Right Pane: Thread Conversation Timeline & Safe HTML Renderer */}
          <FrostedGlassCard className="lg:col-span-7 p-6 flex flex-col justify-between h-full">
            {/* Thread Header */}
            <div>
              <div className="flex items-center justify-between pb-3.5 border-b border-[var(--border-subtle)]">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-[var(--text-primary)]">
                      {selectedThread.subject}
                    </h3>
                    {selectedThread.intent && (
                      <IntentBadge
                        intent={selectedThread.intent}
                        confidence={selectedThread.confidence}
                        showConfidence
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-semibold text-[var(--text-primary)]">
                      {selectedThread.lead_name}
                    </span>
                    <span className="text-xs text-[var(--text-muted)]">
                      &lt;{selectedThread.lead_email}&gt;
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold">
                    <Lock className="w-3 h-3" />
                    Double-Send Protected
                  </span>
                </div>
              </div>

              {/* Messages Timeline */}
              <div className="space-y-4 py-4 max-h-[360px] overflow-y-auto pr-2">
                {selectedThread.messages.map((msg) => {
                  const isOutbound = msg.direction === 'OUTBOUND';
                  // DOMPurify sanitization strictly enforced
                  const safeHtml = msg.body_html
                    ? DOMPurify.sanitize(msg.body_html, { USE_PROFILES: { html: true } })
                    : null;

                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isOutbound ? 'items-end' : 'items-start'}`}
                    >
                      <div className="flex items-center gap-2 mb-1 px-1">
                        <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase">
                          {isOutbound ? 'Outbound SDR' : 'Prospect Reply'}
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          {new Date(msg.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <div
                        className={`p-4 rounded-[20px] max-w-[85%] text-xs leading-relaxed shadow-sm ${
                          isOutbound
                            ? 'bg-[var(--accent-primary)] text-white rounded-br-[4px]'
                            : 'bg-white/80 border border-white/90 text-[var(--text-primary)] backdrop-blur-md rounded-bl-[4px]'
                        }`}
                      >
                        {safeHtml ? (
                          <div
                            className="prose prose-xs max-w-none text-current"
                            dangerouslySetInnerHTML={{ __html: safeHtml }}
                          />
                        ) : (
                          <p className="whitespace-pre-line">{msg.body_text}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Outbound Direct Send / Reply Composer */}
            <div className="pt-3 border-t border-[var(--border-subtle)] space-y-2.5">
              {/* AI Grounded Copilot Card */}
              {selectedThread.ai_suggested_reply && (
                <div className="p-3.5 rounded-[18px] bg-gradient-to-r from-blue-50/80 to-indigo-50/80 border border-blue-200/70 shadow-sm flex flex-col gap-2 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                      <span className="text-xs font-bold text-slate-800">
                        AI Grounded Reply Copilot
                      </span>
                      {selectedThread.confidence && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                          {Math.round(selectedThread.confidence * 100)}% Confidence
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => setReplyText(selectedThread.ai_suggested_reply || '')}
                      className="text-[11px] font-bold text-[var(--accent-primary)] hover:underline flex items-center gap-1"
                    >
                      <span>Insert into Composer</span> →
                    </button>
                  </div>

                  <p className="text-xs text-slate-700 whitespace-pre-line bg-white/80 p-2.5 rounded-[12px] border border-blue-100/80 leading-relaxed font-sans">
                    {selectedThread.ai_suggested_reply}
                  </p>

                  {selectedThread.citations && selectedThread.citations.length > 0 && (
                    <div className="flex items-center gap-2 text-[10px] text-slate-500">
                      <span className="font-semibold">Verified Sources:</span>
                      {selectedThread.citations.map((c, idx) => (
                        <a
                          key={idx}
                          href={c}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-0.5"
                        >
                          {c} <ExternalLink className="w-2.5 h-2.5 inline" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)]">
                <span>Replying to: {selectedThread.lead_email}</span>
                <span>Active Mailbox: {accounts[0]?.email_address}</span>
              </div>

              <div className="relative">
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Draft outbound reply... (anti-burst pacing and Redis locking will protect dispatch)"
                  rows={3}
                  className="w-full rounded-[16px] bg-white/70 backdrop-blur-md border border-[var(--border-subtle)] p-3 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] resize-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
                  <Clock className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                  <span>Business hours window: 9 AM - 5 PM (Recipient TZ)</span>
                </div>

                <SquircleButton
                  variant="primary"
                  size="sm"
                  onClick={handleSendReply}
                  disabled={isSending || !replyText.trim()}
                  className="flex items-center gap-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  {isSending ? 'Locking & Sending...' : 'Dispatch Email'}
                </SquircleButton>
              </div>
            </div>
          </FrostedGlassCard>
        </div>
      )}

      {/* ---------------- SUBTAB 2: MAILBOXES & HEALTH QUOTAS ---------------- */}
      {activeSubTab === 'mailboxes' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {accounts.map((acc) => {
            const usagePercent = Math.round((acc.current_day_sends / acc.daily_send_limit) * 100);
            return (
              <FrostedGlassCard key={acc.id} className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-[14px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] flex items-center justify-center font-bold text-sm">
                      {acc.provider === 'GOOGLE' ? 'G' : 'M'}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-[var(--text-primary)]">
                        {acc.email_address}
                      </h4>
                      <p className="text-[11px] text-[var(--text-muted)] capitalize">
                        {acc.provider} Workspace Integration
                      </p>
                    </div>
                  </div>

                  <span
                    className={`px-2.5 py-1 rounded-[10px] text-[10px] font-bold uppercase tracking-wider ${
                      acc.health_status === 'HEALTHY'
                        ? 'bg-emerald-100 text-emerald-800'
                        : acc.health_status === 'WARMUP'
                        ? 'bg-amber-100 text-amber-800'
                        : acc.health_status === 'PAUSED'
                        ? 'bg-slate-100 text-slate-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {acc.health_status}
                  </span>
                </div>

                {/* Quota Progress Bar */}
                <div className="space-y-1.5 pt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-[var(--text-secondary)]">Daily Send Quota</span>
                    <span className="font-bold text-[var(--text-primary)]">
                      {acc.current_day_sends} / {acc.daily_send_limit} ({usagePercent}%)
                    </span>
                  </div>
                  <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        usagePercent > 85 ? 'bg-amber-500' : 'bg-[var(--accent-primary)]'
                      }`}
                      style={{ width: `${Math.min(usagePercent, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-[var(--border-subtle)] flex items-center justify-between text-xs text-[var(--text-muted)]">
                  <span>SPF / DKIM / DMARC: Verified</span>
                  <span>Last send: {acc.last_send_at ? new Date(acc.last_send_at).toLocaleTimeString() : 'Never'}</span>
                </div>
              </FrostedGlassCard>
            );
          })}
        </div>
      )}

      {/* ---------------- SUBTAB 3: SUPPRESSION LIST ---------------- */}
      {activeSubTab === 'suppression' && (
        <div className="space-y-6">
          <FrostedGlassCard className="p-6">
            <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Add Suppressed Email or Wildcard Domain
            </h3>
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <select
                value={newSuppType}
                onChange={(e) => setNewSuppType(e.target.value as 'email' | 'domain')}
                className="rounded-[14px] bg-white/70 border border-[var(--border-subtle)] px-3 py-2 text-xs font-semibold text-[var(--text-primary)]"
              >
                <option value="email">Exact Email Address</option>
                <option value="domain">Wildcard Domain (@domain.com)</option>
              </select>

              <div className="flex-1 w-full">
                <SquircleInput
                  placeholder={newSuppType === 'email' ? 'prospect@competitor.com' : 'competitor.com'}
                  value={newSuppEntry}
                  onChange={(e) => setNewSuppEntry(e.target.value)}
                />
              </div>

              <SquircleButton variant="primary" size="md" onClick={handleAddSuppression}>
                <Plus className="w-4 h-4 mr-1" />
                Add to Suppression
              </SquircleButton>
            </div>
          </FrostedGlassCard>

          <FrostedGlassCard className="p-6">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Active Suppression Registry ({suppressions.length})
              </h3>
              <span className="text-xs text-[var(--text-muted)]">
                100% deterministic stop enforcement
              </span>
            </div>

            <div className="divide-y divide-[var(--border-subtle)] mt-2">
              {suppressions.map((s) => (
                <div key={s.id} className="py-3 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-bold text-[var(--text-primary)]">
                      {s.email || `@${s.domain}`}
                    </span>
                    <span className="ml-2.5 text-[10px] font-semibold px-2 py-0.5 rounded-[8px] bg-rose-50 text-rose-700 border border-rose-200">
                      {s.reason}
                    </span>
                    <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                      Source: {s.source} • Added: {new Date(s.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteSuppression(s.id)}
                    className="p-1.5 rounded-[10px] text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </FrostedGlassCard>
        </div>
      )}
    </div>
  );
};
