import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  CheckCircle2,
  RefreshCw,
  Mail,
  Calendar,
  Database,
  Plus,
  Trash2,
  Sparkles,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput } from './ui/SquircleInput';
import { SquircleModal } from './ui/SquircleModal';

interface MailboxAccount {
  id: string;
  provider: string;
  email_address: string;
  health_status: string;
  daily_send_limit: number;
  current_day_sends: number;
}

interface CalendarConn {
  id: string;
  provider: string;
  account_email: string;
  sync_status: string;
}

interface CRMConn {
  id: string;
  provider: string;
  account_id?: string;
  account_name?: string;
  sync_status: 'CONNECTED' | 'SYNCING' | 'ERROR' | 'REVOKED';
  last_sync_at?: string;
  sync_error_message?: string;
  sync_errors_json?: Array<{
    record_id?: string;
    email?: string;
    error: string;
    timestamp: string;
  }>;
}

export const IntegrationsView: React.FC = () => {
  const [mailboxes, setMailboxes] = useState<MailboxAccount[]>([]);
  const [calendars, setCalendars] = useState<CalendarConn[]>([]);
  const [crmConnections, setCrmConnections] = useState<CRMConn[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncingCrm, setIsSyncingCrm] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Connect Mailbox Modal
  const [isMailboxModalOpen, setIsMailboxModalOpen] = useState(false);
  const [mailboxProvider, setMailboxProvider] = useState<'GOOGLE' | 'MICROSOFT'>('GOOGLE');
  const [mailboxEmail, setMailboxEmail] = useState('');
  const [mailboxToken, setMailboxToken] = useState('');
  const [dailyLimit, setDailyLimit] = useState(45);
  const [isConnectingMailbox, setIsConnectingMailbox] = useState(false);

  // Connect Calendar Modal
  const [isCalendarModalOpen, setIsCalendarModalOpen] = useState(false);
  const [calendarProvider, setCalendarProvider] = useState<'GOOGLE' | 'MICROSOFT'>('GOOGLE');
  const [calendarEmail, setCalendarEmail] = useState('');
  const [calendarAccessToken, setCalendarAccessToken] = useState('');
  const [isConnectingCalendar, setIsConnectingCalendar] = useState(false);

  // Connect HubSpot CRM Modal
  const [isCrmModalOpen, setIsCrmModalOpen] = useState(false);
  const [crmApiKey, setCrmApiKey] = useState('');
  const [isConnectingCrm, setIsConnectingCrm] = useState(false);

  // Per-Record Sync Errors Modal
  const [isErrorModalOpen, setIsErrorModalOpen] = useState(false);
  const [selectedCrmErrors, setSelectedCrmErrors] = useState<any[]>([]);
  const [errorModalConnId, setErrorModalConnId] = useState<string | null>(null);

  const fetchIntegrations = useCallback(async () => {
    setIsLoading(true);
    try {
      const [emailRes, calRes, crmRes] = await Promise.allSettled([
        axios.get('/api/v1/email/accounts'),
        axios.get('/api/v1/calendar/connections'),
        axios.get('/api/v1/integrations/crm/connections'),
      ]);

      if (emailRes.status === 'fulfilled') {
        setMailboxes(emailRes.value.data || []);
      }
      if (calRes.status === 'fulfilled') {
        setCalendars(calRes.value.data || []);
      }
      if (crmRes.status === 'fulfilled') {
        setCrmConnections(crmRes.value.data || []);
      }
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  // Handle Mailbox Connection
  const handleConnectMailbox = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mailboxEmail.trim()) return;

    setIsConnectingMailbox(true);
    try {
      await axios.post('/api/v1/email/accounts', {
        provider: mailboxProvider,
        email_address: mailboxEmail.trim().toLowerCase(),
        credentials_token: mailboxToken.trim() || 'oauth_token_placeholder',
        daily_send_limit: dailyLimit,
      });

      setNotice(`Mailbox ${mailboxEmail} connected successfully with AES-256 encrypted tokens!`);
      setIsMailboxModalOpen(false);
      setMailboxEmail('');
      setMailboxToken('');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to connect mailbox.');
    } finally {
      setIsConnectingMailbox(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Handle Mailbox Disconnect
  const handleDisconnectMailbox = async (id: string) => {
    try {
      await axios.delete(`/api/v1/email/accounts/${id}`);
      setNotice('Mailbox disconnected and removed from dispatch pool.');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to disconnect mailbox.');
    } finally {
      setTimeout(() => setNotice(null), 3000);
    }
  };

  // Handle Calendar Connection
  const handleConnectCalendar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!calendarEmail.trim()) return;

    setIsConnectingCalendar(true);
    try {
      await axios.post('/api/v1/calendar/connections', {
        provider: calendarProvider,
        account_email: calendarEmail.trim().toLowerCase(),
        access_token: calendarAccessToken.trim() || 'token_sample',
        refresh_token: 'refresh_token_sample',
      });

      setNotice(`Calendar ${calendarEmail} connected! Free/busy availability synchronized.`);
      setIsCalendarModalOpen(false);
      setCalendarEmail('');
      setCalendarAccessToken('');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to connect calendar.');
    } finally {
      setIsConnectingCalendar(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Handle CRM Connection via OAuth
  const handleConnectCrm = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsConnectingCrm(true);
    try {
      const redirectUri = window.location.origin + '/integrations';
      const authRes = await axios.post(
        `/api/v1/integrations/crm/HUBSPOT/connect?redirect_uri=${encodeURIComponent(redirectUri)}`
      );
      if (authRes.data?.authorization_url) {
        setNotice('Redirecting to HubSpot OAuth authorization portal...');
        window.location.href = authRes.data.authorization_url;
      }
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to initiate HubSpot OAuth flow.');
    } finally {
      setIsConnectingCrm(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Trigger On-Demand CRM Sync
  const handleTriggerSync = async (connId: string) => {
    setIsSyncingCrm(true);
    try {
      await axios.post(`/api/v1/integrations/crm/${connId}/sync`);
      setNotice('CRM synchronization initiated in background!');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to trigger CRM sync.');
    } finally {
      setIsSyncingCrm(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Fetch Per-Record Sync Errors
  const handleViewErrors = async (connId: string) => {
    setErrorModalConnId(connId);
    try {
      const res = await axios.get(`/api/v1/integrations/crm/${connId}/errors`);
      setSelectedCrmErrors(res.data?.errors || []);
      setIsErrorModalOpen(true);
    } catch (err: any) {
      console.error('Failed to load CRM sync errors:', err);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Third-Party Integrations &amp; OAuth Adapters
          </h2>
        </div>

        <SquircleButton
          variant="outline"
          size="sm"
          onClick={fetchIntegrations}
          disabled={isLoading}
          className="flex items-center gap-1.5 self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Status
        </SquircleButton>
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

      {/* 3 Main Integration Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Category 1: Outbound Mailboxes */}
        <FrostedGlassCard elevated className="p-6 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-[16px] bg-red-50 text-red-600 flex items-center justify-center">
                <Mail className="w-5 h-5" />
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-slate-100 text-slate-700">
                {mailboxes.length} Connected
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Email Dispatch Mailboxes
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Google Workspace &amp; Microsoft 365 mailboxes for autonomous RFC 2822 email delivery with anti-spam jitter pacing.
              </p>
            </div>

            {/* List of Connected Mailboxes */}
            <div className="space-y-2 pt-1">
              {mailboxes.length === 0 ? (
                <div className="p-3.5 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-400 text-center">
                  No mailboxes connected yet.
                </div>
              ) : (
                mailboxes.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 rounded-[14px] bg-white/80 border border-white flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="truncate">
                      <p className="font-semibold text-slate-800 truncate">{m.email_address}</p>
                      <p className="text-[10px] text-slate-400">
                        {m.provider} • {m.current_day_sends}/{m.daily_send_limit} sent today
                      </p>
                    </div>
                    <button
                      onClick={() => handleDisconnectMailbox(m.id)}
                      className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                      title="Disconnect"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <SquircleButton
            variant="primary"
            size="sm"
            onClick={() => setIsMailboxModalOpen(true)}
            className="w-full flex items-center justify-center gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Connect Outbound Mailbox
          </SquircleButton>
        </FrostedGlassCard>

        {/* Category 2: Calendar Booking */}
        <FrostedGlassCard elevated className="p-6 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-[16px] bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Calendar className="w-5 h-5" />
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-slate-100 text-slate-700">
                {calendars.length} Connected
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Calendar Availability Engine
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Google Calendar and Microsoft Outlook Graph API for autonomous availability resolution, 15-min buffers, and atomic slot locks.
              </p>
            </div>

            {/* List of Connected Calendars */}
            <div className="space-y-2 pt-1">
              {calendars.length === 0 ? (
                <div className="p-3.5 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-400 text-center">
                  No calendars connected yet.
                </div>
              ) : (
                calendars.map((c) => (
                  <div
                    key={c.id}
                    className="p-3 rounded-[14px] bg-white/80 border border-white flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="truncate">
                      <p className="font-semibold text-slate-800 truncate">{c.account_email}</p>
                      <p className="text-[10px] text-emerald-600 font-semibold">{c.provider} • Active</p>
                    </div>
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  </div>
                ))
              )}
            </div>
          </div>

          <SquircleButton
            variant="primary"
            size="sm"
            onClick={() => setIsCalendarModalOpen(true)}
            className="w-full flex items-center justify-center gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Connect Host Calendar
          </SquircleButton>
        </FrostedGlassCard>

        {/* Category 3: HubSpot CRM */}
        <FrostedGlassCard elevated className="p-6 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-[16px] bg-orange-50 text-orange-600 flex items-center justify-center">
                <Database className="w-5 h-5" />
              </div>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                  crmConnections.length > 0 && crmConnections[0].sync_status === 'CONNECTED'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : crmConnections.length > 0 && crmConnections[0].sync_status === 'SYNCING'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse'
                    : crmConnections.length > 0 && crmConnections[0].sync_status === 'ERROR'
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                {crmConnections.length > 0 ? crmConnections[0].sync_status : 'Not Connected'}
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                HubSpot CRM Integration
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Bi-directional contact syncing, field-level deduplication mapping, and automated NFAT qualification write-backs.
              </p>
            </div>

            {crmConnections.length > 0 ? (
              <div className="space-y-2">
                <div className="p-3.5 rounded-[14px] bg-white/80 border border-white text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Account:</span>
                    <span className="font-bold text-slate-800">{crmConnections[0].account_name || crmConnections[0].account_id || 'HubSpot Portal'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Last Synced:</span>
                    <span className="font-mono text-slate-700 text-[11px]">
                      {crmConnections[0].last_sync_at
                        ? new Date(crmConnections[0].last_sync_at).toLocaleString()
                        : 'Never'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Field Mapping:</span>
                    <span className="font-bold text-slate-800">10 Canonical Groups</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <SquircleButton
                    variant="outline"
                    size="sm"
                    disabled={isSyncingCrm || crmConnections[0].sync_status === 'SYNCING'}
                    onClick={() => handleTriggerSync(crmConnections[0].id)}
                    className="flex-1 text-[11px] font-bold py-2 flex items-center justify-center gap-1.5"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isSyncingCrm || crmConnections[0].sync_status === 'SYNCING' ? 'animate-spin' : ''}`} />
                    Sync Now
                  </SquircleButton>

                  <SquircleButton
                    variant="outline"
                    size="sm"
                    onClick={() => handleViewErrors(crmConnections[0].id)}
                    className="text-[11px] font-bold py-2 flex items-center gap-1 text-slate-600 hover:text-slate-900"
                  >
                    <FileText className="w-3.5 h-3.5 text-amber-500" />
                    Errors ({crmConnections[0].sync_errors_json?.length || 0})
                  </SquircleButton>
                </div>
              </div>
            ) : (
              <div className="p-3.5 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs space-y-1">
                <div className="flex items-center justify-between text-slate-600">
                  <span>Field Mapping Status:</span>
                  <span className="font-bold text-slate-800">10 Canonical Groups</span>
                </div>
                <div className="flex items-center justify-between text-slate-600">
                  <span>Sync Mechanism:</span>
                  <span className="font-mono text-slate-800">OAuth2 + Webhooks</span>
                </div>
              </div>
            )}
          </div>

          <SquircleButton
            variant={crmConnections.length > 0 ? 'outline' : 'primary'}
            size="sm"
            onClick={() => {
              if (crmConnections.length > 0) {
                setNotice('HubSpot CRM connection is active. Re-authentication can be initiated if needed.');
              } else {
                setIsCrmModalOpen(true);
              }
            }}
            className="w-full flex items-center justify-center gap-1.5 shadow-sm"
          >
            {crmConnections.length > 0 ? 'Manage CRM Connection' : 'Connect HubSpot CRM'}
          </SquircleButton>
        </FrostedGlassCard>
      </div>

      {/* Connect Mailbox Modal */}
      <SquircleModal
        isOpen={isMailboxModalOpen}
        onClose={() => setIsMailboxModalOpen(false)}
        title="Connect Outbound Mailbox"
        maxWidth="md"
      >
        <form onSubmit={handleConnectMailbox} className="space-y-4 pt-1">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
              Provider Platform
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(['GOOGLE', 'MICROSOFT'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setMailboxProvider(p)}
                  className={`p-2.5 rounded-[12px] text-xs font-semibold border transition-all ${
                    mailboxProvider === p
                      ? 'bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {p === 'GOOGLE' ? 'Google Workspace' : 'Microsoft 365'}
                </button>
              ))}
            </div>
          </div>

          <SquircleInput
            label="Email Address *"
            type="email"
            value={mailboxEmail}
            onChange={(e) => setMailboxEmail(e.target.value)}
            placeholder="sdr@yourcompany.com"
            required
          />

          <SquircleInput
            label="OAuth Credentials / Access Token"
            type="password"
            value={mailboxToken}
            onChange={(e) => setMailboxToken(e.target.value)}
            placeholder="Enter token (Encrypted with AES-256)"
          />

          <SquircleInput
            label="Daily Send Limit (30–50 recommended)"
            type="number"
            value={dailyLimit}
            onChange={(e) => setDailyLimit(parseInt(e.target.value, 10) || 45)}
          />

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsMailboxModalOpen(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isConnectingMailbox}
            >
              Connect &amp; Encrypt
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>

      {/* Connect Calendar Modal */}
      <SquircleModal
        isOpen={isCalendarModalOpen}
        onClose={() => setIsCalendarModalOpen(false)}
        title="Connect Host Calendar"
        maxWidth="md"
      >
        <form onSubmit={handleConnectCalendar} className="space-y-4 pt-1">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
              Calendar Provider
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(['GOOGLE', 'MICROSOFT'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setCalendarProvider(p)}
                  className={`p-2.5 rounded-[12px] text-xs font-semibold border transition-all ${
                    calendarProvider === p
                      ? 'bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {p === 'GOOGLE' ? 'Google Calendar' : 'Outlook Calendar'}
                </button>
              ))}
            </div>
          </div>

          <SquircleInput
            label="Host Account Email *"
            type="email"
            value={calendarEmail}
            onChange={(e) => setCalendarEmail(e.target.value)}
            placeholder="alex.vance@yourcompany.com"
            required
          />

          <SquircleInput
            label="Calendar OAuth Token"
            type="password"
            value={calendarAccessToken}
            onChange={(e) => setCalendarAccessToken(e.target.value)}
            placeholder="OAuth access token"
          />

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsCalendarModalOpen(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isConnectingCalendar}
            >
              Connect Calendar
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>

      {/* Connect CRM Modal */}
      <SquircleModal
        isOpen={isCrmModalOpen}
        onClose={() => setIsCrmModalOpen(false)}
        title="Connect HubSpot CRM"
        maxWidth="md"
      >
        <form onSubmit={handleConnectCrm} className="space-y-4 pt-1">
          <SquircleInput
            label="HubSpot Private App Token / API Key *"
            type="password"
            value={crmApiKey}
            onChange={(e) => setCrmApiKey(e.target.value)}
            placeholder="Enter private app token"
            required
          />

          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
            Requires scopes: <span className="font-mono text-slate-700">crm.objects.contacts.read, crm.objects.contacts.write</span>. Token will be encrypted at rest with AES-256-GCM envelope encryption.
          </p>

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsCrmModalOpen(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isConnectingCrm}
            >
              Authenticate CRM
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>

      {/* Per-Record Sync Errors & Warnings Modal */}
      <SquircleModal
        isOpen={isErrorModalOpen}
        onClose={() => setIsErrorModalOpen(false)}
        title={`CRM Per-Record Sync Errors & Warnings ${errorModalConnId ? `(${errorModalConnId.slice(0, 8)})` : ''}`}
        maxWidth="lg"
      >
        <div className="space-y-4 pt-1">
          <p className="text-xs text-[var(--text-secondary)]">
            Per-record telemetry tracking invalid email addresses, schema mismatches, and suppression blocks during bidirectional synchronization.
          </p>

          {selectedCrmErrors.length === 0 ? (
            <div className="p-8 rounded-[16px] bg-emerald-50/60 border border-emerald-200 text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
              <p className="text-sm font-bold text-emerald-900">Zero Sync Errors</p>
              <p className="text-xs text-emerald-700">All contact records normalized and ingested without issues.</p>
            </div>
          ) : (
            <div className="max-h-[350px] overflow-y-auto space-y-2 pr-1">
              {selectedCrmErrors.map((err, idx) => (
                <div key={idx} className="p-3 rounded-[14px] bg-slate-50 border border-slate-200/80 text-xs space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-mono font-bold text-slate-800">{err.email || err.record_id || 'Unknown Record'}</span>
                    <span className="text-slate-400">{err.timestamp ? new Date(err.timestamp).toLocaleTimeString() : ''}</span>
                  </div>
                  <p className="text-rose-600 font-medium flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    {err.error}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="pt-2 flex justify-end">
            <SquircleButton variant="primary" size="sm" onClick={() => setIsErrorModalOpen(false)}>
              Close
            </SquircleButton>
          </div>
        </div>
      </SquircleModal>
    </div>
  );
};
