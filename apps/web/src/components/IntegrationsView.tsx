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
  Key,
  ExternalLink,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  HelpCircle,
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
  provider: 'HUBSPOT' | 'SALESFORCE' | 'PIPEDRIVE' | 'ZOHO';
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

type SupportedCRM = 'HUBSPOT' | 'SALESFORCE' | 'PIPEDRIVE' | 'ZOHO';

interface CRMDefinition {
  id: SupportedCRM;
  name: string;
  accentColor: string;
  badgeBg: string;
  badgeText: string;
  description: string;
  keyLabel: string;
  keyPlaceholder: string;
  helpTitle: string;
  helpSteps: string[];
  scopes: string[];
  docUrl: string;
  requiresInstanceUrl: boolean;
  instanceUrlLabel?: string;
  instanceUrlPlaceholder?: string;
}

const CRM_DEFINITIONS: CRMDefinition[] = [
  {
    id: 'HUBSPOT',
    name: 'HubSpot CRM',
    accentColor: '#FF7A59',
    badgeBg: 'bg-orange-50',
    badgeText: 'text-orange-600',
    description: 'Bi-directional contacts sync, deal lifecycle stages, and automated SDR qualification write-backs.',
    keyLabel: 'HubSpot Private App Access Token (pat-...) *',
    keyPlaceholder: 'pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
    helpTitle: 'HubSpot Private App Access Token Kaise Generate Karein?',
    helpSteps: [
      'HubSpot Dashboard mein login karein aur top-right Settings (gear icon ⚙️) par click karein.',
      'Left sidebar menu se Integrations -> Private Apps select karein.',
      'Create a private app button par click karein aur app ka name dein (e.g. AI SDR Sync).',
      'Scopes tab mein jayein aur crm.objects.contacts.read aur crm.objects.contacts.write tick karein.',
      'Create app click karein, popup mein Continue creating confirm karein aur generate hone wala Token (starts with pat-...) copy karke yahan paste karein.'
    ],
    scopes: ['crm.objects.contacts.read', 'crm.objects.contacts.write'],
    docUrl: 'https://developers.hubspot.com/docs/api/private-apps',
    requiresInstanceUrl: false,
  },
  {
    id: 'SALESFORCE',
    name: 'Salesforce CRM',
    accentColor: '#00A1E0',
    badgeBg: 'bg-sky-50',
    badgeText: 'text-sky-600',
    description: 'Enterprise SOQL Lead synchronization, cursor-based pagination, and bidirectional status updates.',
    keyLabel: 'Connected App Access Token / Session Token *',
    keyPlaceholder: '00D8c0000086XYZ!AQEAQ... (Bearer / Session Token)',
    helpTitle: 'Salesforce Connected App Credentials Kaise Hasil Karein?',
    helpSteps: [
      'Salesforce Setup (gear icon ⚙️) mein jayein aur App Manager search karein.',
      'New Connected App banayein aur Enable OAuth Settings check karein.',
      'Selected OAuth Scopes mein api (Manage user data via APIs) aur refresh_token shamil karein.',
      'Apna Salesforce Instance URL (e.g., https://yourcompany.my.salesforce.com) aur Access Token yahan provide karein.'
    ],
    scopes: ['api (Access and manage data)', 'refresh_token, offline_access'],
    docUrl: 'https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/',
    requiresInstanceUrl: true,
    instanceUrlLabel: 'Salesforce Instance URL *',
    instanceUrlPlaceholder: 'https://yourcompany.my.salesforce.com',
  },
  {
    id: 'PIPEDRIVE',
    name: 'Pipedrive CRM',
    accentColor: '#00B050',
    badgeBg: 'bg-emerald-50',
    badgeText: 'text-emerald-600',
    description: 'Fast Persons & Organization syncing, multi-email resolution, and instant deal/lead qualification.',
    keyLabel: 'Personal API Token (40-char string) *',
    keyPlaceholder: '40-character API token (e.g. 8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6071)',
    helpTitle: 'Pipedrive Personal API Token Kahan se Milega?',
    helpSteps: [
      'Pipedrive account mein login karein.',
      'Top-right avatar par click karein aur Personal preferences select karein.',
      'API tab par click karein.',
      'Apna 40-character Personal API token copy karein aur yahan paste karein.'
    ],
    scopes: ['contacts:read', 'contacts:full'],
    docUrl: 'https://pipedrive.readme.io/docs/how-to-find-the-api-token',
    requiresInstanceUrl: false,
  },
  {
    id: 'ZOHO',
    name: 'Zoho CRM',
    accentColor: '#E42528',
    badgeBg: 'bg-red-50',
    badgeText: 'text-red-600',
    description: 'Zoho CRM Leads module sync, country/currency revenue mapping, and opt-out synchronization.',
    keyLabel: 'Zoho API Access / Refresh Token *',
    keyPlaceholder: '1000.xxxx.xxxx (Zoho OAuth Token)',
    helpTitle: 'Zoho CRM API Token & Data Center Domain Kaise Configure Karein?',
    helpSteps: [
      'Zoho API Console (https://api-console.zoho.com) open karein.',
      'Add Client click karein aur Self Client select karein.',
      'Scope enter karein: ZohoCRM.modules.leads.ALL,ZohoCRM.modules.contacts.ALL.',
      'Generate code click karein aur generate hone wala Token aur apna API domain (e.g. https://www.zohoapis.com) yahan paste karein.'
    ],
    scopes: ['ZohoCRM.modules.leads.ALL', 'ZohoCRM.modules.contacts.ALL'],
    docUrl: 'https://www.zoho.com/crm/developer/docs/api/v3/oauth-overview.html',
    requiresInstanceUrl: true,
    instanceUrlLabel: 'Zoho API Domain / Data Center *',
    instanceUrlPlaceholder: 'https://www.zohoapis.com (or .eu / .in)',
  },
];

export const IntegrationsView: React.FC = () => {
  const [mailboxes, setMailboxes] = useState<MailboxAccount[]>([]);
  const [calendars, setCalendars] = useState<CalendarConn[]>([]);
  const [crmConnections, setCrmConnections] = useState<CRMConn[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncingCrm, setIsSyncingCrm] = useState<string | null>(null);
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

  // Connect CRM Modal
  const [isCrmModalOpen, setIsCrmModalOpen] = useState(false);
  const [selectedCrmProvider, setSelectedCrmProvider] = useState<SupportedCRM>('HUBSPOT');
  const [crmAuthMode, setCrmAuthMode] = useState<'KEY' | 'OAUTH'>('KEY');
  const [crmApiKey, setCrmApiKey] = useState('');
  const [crmInstanceUrl, setCrmInstanceUrl] = useState('');
  const [crmAccountName, setCrmAccountName] = useState('');
  const [isConnectingCrm, setIsConnectingCrm] = useState(false);

  // Guide Drawer state
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [guideActiveTab, setGuideActiveTab] = useState<SupportedCRM>('HUBSPOT');

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

  // Open CRM Modal pre-selected
  const handleOpenCrmModal = (provider: SupportedCRM) => {
    setSelectedCrmProvider(provider);
    setCrmApiKey('');
    setCrmInstanceUrl(provider === 'ZOHO' ? 'https://www.zohoapis.com' : '');
    setCrmAccountName('');
    setCrmAuthMode('KEY');
    setIsCrmModalOpen(true);
  };

  // Direct Connect via API Key / Access Token
  const handleConnectCrmDirect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!crmApiKey.trim()) return;

    setIsConnectingCrm(true);
    try {
      await axios.post('/api/v1/integrations/crm/connect-key', {
        provider: selectedCrmProvider,
        api_key: crmApiKey.trim(),
        instance_url: crmInstanceUrl.trim() || undefined,
        account_name: crmAccountName.trim() || undefined,
      });

      setNotice(`${selectedCrmProvider} connected successfully with AES-256 encrypted credentials! Initial sync started.`);
      setIsCrmModalOpen(false);
      setCrmApiKey('');
      setCrmInstanceUrl('');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to connect CRM.');
    } finally {
      setIsConnectingCrm(false);
      setTimeout(() => setNotice(null), 5000);
    }
  };

  // Handle CRM Connection via OAuth
  const handleConnectCrmOAuth = async () => {
    setIsConnectingCrm(true);
    try {
      const redirectUri = window.location.origin + '/integrations';
      const authRes = await axios.post(
        `/api/v1/integrations/crm/${selectedCrmProvider}/connect?redirect_uri=${encodeURIComponent(redirectUri)}`
      );
      if (authRes.data?.authorization_url) {
        setNotice(`Redirecting to ${selectedCrmProvider} OAuth authorization portal...`);
        window.location.href = authRes.data.authorization_url;
      }
    } catch (err: any) {
      setNotice(err.response?.data?.detail || `Failed to initiate ${selectedCrmProvider} OAuth flow.`);
    } finally {
      setIsConnectingCrm(false);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Trigger On-Demand CRM Sync
  const handleTriggerSync = async (connId: string) => {
    setIsSyncingCrm(connId);
    try {
      await axios.post(`/api/v1/integrations/crm/${connId}/sync`);
      setNotice('CRM synchronization initiated in background!');
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to trigger CRM sync.');
    } finally {
      setIsSyncingCrm(null);
      setTimeout(() => setNotice(null), 4000);
    }
  };

  // Disconnect CRM Connection
  const handleDisconnectCrm = async (connId: string, providerName: string) => {
    if (!window.confirm(`Are you sure you want to disconnect ${providerName}? Contacts in AI SDR will remain, but automatic sync will stop.`)) {
      return;
    }
    try {
      await axios.delete(`/api/v1/integrations/crm/${connId}`);
      setNotice(`${providerName} disconnected successfully.`);
      await fetchIntegrations();
    } catch (err: any) {
      setNotice(err.response?.data?.detail || 'Failed to disconnect CRM.');
    } finally {
      setTimeout(() => setNotice(null), 3000);
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

  const currentDef = CRM_DEFINITIONS.find((d) => d.id === selectedCrmProvider) || CRM_DEFINITIONS[0];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Third-Party Integrations &amp; CRM Ecosystem
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Enterprise mailboxes, host calendars, and bi-directional CRM adapters with AES-256-GCM encrypted credentials.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <SquircleButton
            variant="outline"
            size="sm"
            onClick={() => setIsGuideOpen(!isGuideOpen)}
            className="flex items-center gap-1.5 text-xs font-semibold text-[var(--accent-primary)] border-[var(--accent-glow)] bg-[var(--accent-subtle)]"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            CRM API Key Guide
            {isGuideOpen ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
          </SquircleButton>

          <SquircleButton
            variant="outline"
            size="sm"
            onClick={fetchIntegrations}
            disabled={isLoading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </SquircleButton>
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/60 text-xs text-blue-800 flex items-center justify-between shadow-xs">
          <span className="flex items-center gap-2 font-medium">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            {notice}
          </span>
          <button onClick={() => setNotice(null)} className="text-blue-500 hover:text-blue-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Expandable CRM Setup & API Key Guide */}
      {isGuideOpen && (
        <FrostedGlassCard elevated className="p-6 border-indigo-100 bg-white/90 space-y-4 animate-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-[var(--accent-primary)]" />
              <h3 className="text-sm font-bold text-slate-800">
                CRM Setup &amp; API Key Instructions (Kon Si Key Kahan Se Milegi?)
              </h3>
            </div>
            <span className="text-[11px] text-slate-500 font-medium">
              Step-by-step credentials guide for all CRMs
            </span>
          </div>

          {/* CRM Tabs */}
          <div className="flex flex-wrap gap-2">
            {CRM_DEFINITIONS.map((crm) => (
              <button
                key={crm.id}
                onClick={() => setGuideActiveTab(crm.id)}
                className={`px-3 py-1.5 rounded-[12px] text-xs font-bold transition-all ${
                  guideActiveTab === crm.id
                    ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {crm.name}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {(() => {
            const activeCrm = CRM_DEFINITIONS.find((c) => c.id === guideActiveTab) || CRM_DEFINITIONS[0];
            return (
              <div className="p-4 rounded-[18px] bg-slate-50 border border-slate-200/80 space-y-3 text-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h4 className="font-bold text-slate-900 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: activeCrm.accentColor }} />
                    {activeCrm.helpTitle}
                  </h4>
                  <a
                    href={activeCrm.docUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    Official Docs <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="p-2.5 rounded-[12px] bg-white border border-slate-200 text-slate-700 space-y-1">
                  <span className="font-semibold text-slate-800">Key Type: </span>
                  <code className="text-blue-700 font-mono font-bold bg-blue-50 px-1.5 py-0.5 rounded">
                    {activeCrm.keyLabel.replace('*', '').trim()}
                  </code>
                </div>

                <ol className="space-y-1.5 list-decimal list-inside text-slate-700 leading-relaxed">
                  {activeCrm.helpSteps.map((step, idx) => (
                    <li key={idx} className="pl-1">
                      {step}
                    </li>
                  ))}
                </ol>

                <div className="pt-2 flex flex-wrap items-center gap-2 border-t border-slate-200">
                  <span className="text-[11px] font-bold text-slate-600">Required Scopes:</span>
                  {activeCrm.scopes.map((s, i) => (
                    <span key={i} className="font-mono text-[10px] bg-white border border-slate-200 px-2 py-0.5 rounded-full text-slate-600">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            );
          })()}
        </FrostedGlassCard>
      )}

      {/* Row 1: Mailbox & Calendar Integrations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Category 1: Outbound Mailboxes */}
        <FrostedGlassCard elevated className="p-6 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-[16px] bg-red-50 text-red-600 flex items-center justify-center shadow-xs">
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
            <div className="space-y-2 pt-1 max-h-[160px] overflow-y-auto">
              {mailboxes.length === 0 ? (
                <div className="p-3 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-400 text-center">
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
            Connect Mailbox
          </SquircleButton>
        </FrostedGlassCard>

        {/* Category 2: Host Calendar Engine */}
        <FrostedGlassCard elevated className="p-6 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-[16px] bg-blue-50 text-blue-600 flex items-center justify-center shadow-xs">
                <Calendar className="w-5 h-5" />
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-slate-100 text-slate-700">
                {calendars.length} Connected
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                Host Calendar Engine
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">
                Connect Google Calendar or Microsoft Outlook for real-time free/busy slot computation and autonomous meeting bookings.
              </p>
            </div>

            {/* List of Connected Calendars */}
            <div className="space-y-2 pt-1 max-h-[160px] overflow-y-auto">
              {calendars.length === 0 ? (
                <div className="p-3 rounded-[14px] bg-slate-50 border border-slate-200/60 text-xs text-slate-400 text-center">
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
                      <p className="text-[10px] text-slate-400">
                        {c.provider} • {c.sync_status}
                      </p>
                    </div>
                    <span className="px-2 py-0.5 text-[10px] rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 font-bold">
                      Active
                    </span>
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
      </div>

      {/* Row 2: Enterprise CRM Integrators Suite (HubSpot, Salesforce, Pipedrive, Zoho) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Database className="w-5 h-5 text-[var(--accent-primary)]" />
              Enterprise CRM Integrators Suite
            </h3>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Bi-directional contact syncing, 10 Canonical Groups mapping, and automated SDR qualification write-backs.
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>AES-256-GCM Envelope Encryption</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {CRM_DEFINITIONS.map((def) => {
            const activeConn = crmConnections.find((c) => c.provider === def.id);
            const isSyncing = isSyncingCrm === activeConn?.id || activeConn?.sync_status === 'SYNCING';

            return (
              <FrostedGlassCard
                key={def.id}
                elevated
                className="p-5 flex flex-col justify-between space-y-4 border-white/80"
              >
                <div className="space-y-3">
                  {/* Top Bar */}
                  <div className="flex items-center justify-between">
                    <div
                      className={`w-10 h-10 rounded-[14px] ${def.badgeBg} ${def.badgeText} flex items-center justify-center font-bold text-sm shadow-xs`}
                    >
                      {def.id.slice(0, 2)}
                    </div>

                    <span
                      className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${
                        activeConn && activeConn.sync_status === 'CONNECTED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : isSyncing
                          ? 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse'
                          : activeConn && activeConn.sync_status === 'ERROR'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {activeConn ? activeConn.sync_status : 'Not Connected'}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-slate-800">{def.name}</h4>
                    <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                      {def.description}
                    </p>
                  </div>

                  {activeConn ? (
                    <div className="p-3 rounded-[12px] bg-white/80 border border-slate-200/80 text-[11px] space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Account:</span>
                        <span className="font-bold text-slate-800 truncate max-w-[120px]">
                          {activeConn.account_name || activeConn.account_id || `${def.name} Portal`}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Last Synced:</span>
                        <span className="font-mono text-slate-700 text-[10px]">
                          {activeConn.last_sync_at
                            ? new Date(activeConn.last_sync_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                            : 'Pending'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Mapping:</span>
                        <span className="font-bold text-emerald-700">10 Groups</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-[12px] bg-slate-50 border border-slate-200/60 text-[11px] space-y-1 text-slate-500">
                      <div className="flex items-center justify-between">
                        <span>Key Required:</span>
                        <span className="font-semibold text-slate-700">API Token</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Sync Engine:</span>
                        <span className="font-mono text-slate-700">REST v3/v1</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                {activeConn ? (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center gap-1.5">
                      <SquircleButton
                        variant="outline"
                        size="sm"
                        disabled={isSyncing}
                        onClick={() => handleTriggerSync(activeConn.id)}
                        className="flex-1 text-[11px] font-bold py-1.5 flex items-center justify-center gap-1"
                      >
                        <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
                        Sync
                      </SquircleButton>

                      <SquircleButton
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewErrors(activeConn.id)}
                        className="text-[11px] font-bold py-1.5 px-2 flex items-center gap-1 text-slate-600"
                        title="View sync errors"
                      >
                        <FileText className="w-3 h-3 text-amber-500" />
                        {activeConn.sync_errors_json?.length || 0}
                      </SquircleButton>

                      <button
                        onClick={() => handleDisconnectCrm(activeConn.id, def.name)}
                        className="p-2 text-slate-400 hover:text-rose-600 rounded-[10px] hover:bg-rose-50 transition-colors"
                        title="Disconnect CRM"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <SquircleButton
                    variant="primary"
                    size="sm"
                    onClick={() => handleOpenCrmModal(def.id)}
                    className="w-full text-xs flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Connect {def.name.split(' ')[0]}
                  </SquircleButton>
                )}
              </FrostedGlassCard>
            );
          })}
        </div>
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

      {/* Connect CRM Modal (Multi-CRM Support with Step-by-step Key guidance) */}
      <SquircleModal
        isOpen={isCrmModalOpen}
        onClose={() => setIsCrmModalOpen(false)}
        title={`Connect ${currentDef.name}`}
        maxWidth="lg"
      >
        <div className="space-y-4 pt-1">
          {/* CRM Provider Selector Tabs */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
              Select CRM Provider
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {CRM_DEFINITIONS.map((def) => (
                <button
                  key={def.id}
                  type="button"
                  onClick={() => {
                    setSelectedCrmProvider(def.id);
                    setCrmApiKey('');
                    setCrmInstanceUrl(def.id === 'ZOHO' ? 'https://www.zohoapis.com' : '');
                  }}
                  className={`p-2.5 rounded-[14px] text-xs font-bold border transition-all text-center ${
                    selectedCrmProvider === def.id
                      ? 'bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] shadow-xs'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {def.name.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Connection Mode Toggle */}
          <div className="flex rounded-[12px] bg-slate-100 p-1 text-xs">
            <button
              type="button"
              onClick={() => setCrmAuthMode('KEY')}
              className={`flex-1 py-1.5 rounded-[10px] font-bold transition-all ${
                crmAuthMode === 'KEY'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Direct API Key / Access Token
            </button>
            <button
              type="button"
              onClick={() => setCrmAuthMode('OAUTH')}
              className={`flex-1 py-1.5 rounded-[10px] font-bold transition-all ${
                crmAuthMode === 'OAUTH'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              OAuth 2.0 Login Flow
            </button>
          </div>

          {/* Guidance Box for the selected CRM */}
          <div className="p-3.5 rounded-[16px] bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                {currentDef.helpTitle}
              </span>
              <a
                href={currentDef.docUrl}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                Docs <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <ol className="list-decimal list-inside space-y-1 text-slate-600 text-[11px] leading-relaxed">
              {currentDef.helpSteps.slice(0, 3).map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>

          {crmAuthMode === 'KEY' ? (
            <form onSubmit={handleConnectCrmDirect} className="space-y-3">
              {currentDef.requiresInstanceUrl && (
                <SquircleInput
                  label={currentDef.instanceUrlLabel || 'Instance URL *'}
                  type="text"
                  value={crmInstanceUrl}
                  onChange={(e) => setCrmInstanceUrl(e.target.value)}
                  placeholder={currentDef.instanceUrlPlaceholder || 'https://...'}
                  required
                />
              )}

              <SquircleInput
                label={currentDef.keyLabel}
                type="password"
                value={crmApiKey}
                onChange={(e) => setCrmApiKey(e.target.value)}
                placeholder={currentDef.keyPlaceholder}
                required
              />

              <SquircleInput
                label="Account Label (Optional)"
                type="text"
                value={crmAccountName}
                onChange={(e) => setCrmAccountName(e.target.value)}
                placeholder={`My ${currentDef.name} Workspace`}
              />

              <p className="text-[11px] text-slate-400 leading-relaxed flex items-center gap-1.5 pt-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                Token is securely encrypted at rest using AES-256-GCM envelope encryption.
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
                  Connect &amp; Sync
                </SquircleButton>
              </div>
            </form>
          ) : (
            <div className="space-y-4 pt-2">
              <p className="text-xs text-slate-600 leading-relaxed">
                You will be redirected to the secure <strong>{currentDef.name}</strong> login portal to grant OAuth authorization. Your tokens will be saved with automatic background refreshing.
              </p>

              <div className="p-3 rounded-[12px] bg-blue-50/60 border border-blue-200/60 text-xs text-blue-900 space-y-1">
                <p className="font-semibold">Required Scopes:</p>
                <p className="font-mono text-[11px] text-blue-800">
                  {currentDef.scopes.join(', ')}
                </p>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <SquircleButton
                  variant="outline"
                  type="button"
                  onClick={() => setIsCrmModalOpen(false)}
                >
                  Cancel
                </SquircleButton>
                <SquircleButton
                  variant="primary"
                  type="button"
                  onClick={handleConnectCrmOAuth}
                  isLoading={isConnectingCrm}
                >
                  Continue to {currentDef.name.split(' ')[0]} OAuth
                </SquircleButton>
              </div>
            </div>
          )}
        </div>
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
