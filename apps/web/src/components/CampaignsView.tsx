import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Play,
  Pause,
  Clock,
  ShieldCheck,
  Layers,
  Sparkles,
  Plus,
  RefreshCw,
  Users,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleModal } from './ui/SquircleModal';
import { CampaignBuilderWizard } from './CampaignBuilderWizard';
import { AIPersonalizationModal, OutboundDraftData, ModelTelemetryData } from './AIPersonalizationModal';

interface CampaignStep {
  id?: string;
  step_number: number;
  delay_days: number;
  delay_hours: number;
  prompt_instructions: string;
  template_subject?: string;
  template_body?: string;
  template_config_json?: any;
}

interface CampaignLeadItem {
  id: string;
  lead_name: string;
  company_name: string;
  email: string;
  timezone: string;
  current_step: number;
  state:
    | 'QUEUED'
    | 'WAITING'
    | 'READY'
    | 'SENT'
    | 'REPLIED'
    | 'PAUSED'
    | 'UNSUBSCRIBED'
    | 'BOUNCED'
    | 'MEETING_BOOKED'
    | 'COMPLETED';
  next_action_at: string | null;
}

interface AuditEvent {
  id: string;
  lead_id: string;
  lead_email: string;
  event_type: string;
  rule_matched: string;
  model_version: string;
  prompt_version: string;
  knowledge_chunk_ids: string[];
  previous_state: string;
  new_state: string;
  reason: string;
  created_at: string;
}

interface CampaignItem {
  id: string;
  name: string;
  status: 'DRAFT' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';
  objective: string;
  config_json?: any;
  steps: CampaignStep[];
  total_leads: number;
  active_leads: number;
  completed_leads: number;
  created_at: string;
}

export const CampaignsView: React.FC = () => {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Campaign specific sub-data
  const [leads, setLeads] = useState<CampaignLeadItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [notification, setNotification] = useState<string | null>(null);

  // Modals
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [selectedLeadForPreview, setSelectedLeadForPreview] = useState<CampaignLeadItem | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch all campaigns
  const fetchCampaigns = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await axios.get('/api/v1/campaigns');
      const data: CampaignItem[] = res.data || [];
      setCampaigns(data);

      if (data.length > 0) {
        setSelectedCampaignId((prev) => {
          if (prev && data.some((c) => c.id === prev)) return prev;
          return data[0].id;
        });
      } else {
        setSelectedCampaignId(null);
      }
    } catch (err: any) {
      console.error('Failed to load campaigns:', err);
      setNotification(err.response?.data?.detail || 'Unable to connect to campaign service.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  // Selected Campaign
  const currentCampaign = campaigns.find((c) => c.id === selectedCampaignId) || null;

  // Load selected campaign leads and audit trail
  useEffect(() => {
    if (!currentCampaign) {
      setLeads([]);
      setAuditEvents([]);
      return;
    }

    const loadCampaignDetails = async () => {
      try {
        const [leadsRes, auditRes] = await Promise.allSettled([
          axios.get(`/api/v1/campaigns/${currentCampaign.id}/leads`),
          axios.get(`/api/v1/campaigns/${currentCampaign.id}/audit-events`),
        ]);

        if (leadsRes.status === 'fulfilled') {
          const rawLeads = leadsRes.value.data || [];
          setLeads(
            rawLeads.map((l: any) => ({
              id: l.id,
              lead_name: l.lead_name || 'Prospect',
              company_name: l.company_name || 'Target Account',
              email: l.lead_email || l.email || '',
              timezone: l.timezone || 'UTC',
              current_step: l.current_step || 1,
              state: l.state || 'QUEUED',
              next_action_at: l.next_action_at || null,
            }))
          );
        } else {
          setLeads([]);
        }

        if (auditRes.status === 'fulfilled') {
          const rawEvents = auditRes.value.data || [];
          setAuditEvents(
            rawEvents.map((e: any) => ({
              id: e.id,
              lead_id: e.lead_id || '',
              lead_email: e.data_payload?.lead_email || e.lead_id || 'System Event',
              event_type: e.event_type,
              rule_matched: e.rule_name || 'DETERMINISTIC_SAFEGUARD',
              model_version: e.model_version || 'N/A',
              prompt_version: e.prompt_version || 'N/A',
              knowledge_chunk_ids: e.knowledge_chunk_ids || [],
              previous_state: e.previous_state || 'N/A',
              new_state: e.new_state || 'N/A',
              reason: e.data_payload?.reason || 'Sequence state transition evaluated',
              created_at: e.created_at,
            }))
          );
        } else {
          setAuditEvents([]);
        }
      } catch (err) {
        console.error('Failed to load campaign sub-resources:', err);
      }
    };

    loadCampaignDetails();
  }, [currentCampaign?.id]);

  // Campaign State Transitions
  const handleCampaignAction = async (action: 'start' | 'pause' | 'resume') => {
    if (!currentCampaign) return;
    setActionLoading(true);
    try {
      await axios.post(`/api/v1/campaigns/${currentCampaign.id}/${action}`);
      setNotification(`Campaign transitioned to ${action === 'pause' ? 'PAUSED' : 'RUNNING'}.`);
      await fetchCampaigns();
    } catch (err: any) {
      setNotification(err.response?.data?.detail || `Failed to ${action} campaign.`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setNotification(null), 4000);
    }
  };

  const sampleDraft: OutboundDraftData = {
    subject: currentCampaign?.steps?.[0]?.template_subject || 'Accelerating outbound pipeline',
    body:
      currentCampaign?.steps?.[0]?.template_body ||
      'Hi {{first_name}},\n\nNoticed {{company_name}} is scaling outbound. Codenter AI SDR automates high-fidelity outreach with 100% grounded facts.\n\nOpen to a 10-minute demo?',
    personalization_facts: ['Target Account Leadership', 'Verified ICP Fit'],
    cta: 'Book 10-minute demo call',
    claims_used: ['3.2x more qualified pipeline in 45 days'],
    confidence: 0.94,
    risk_flags: [],
    recommended_action: 'SEND',
  };

  const sampleTelemetry: ModelTelemetryData = {
    model: 'claude-3-5-sonnet-20241022',
    prompt_version: 'v2.0-grounded-outbound',
    prompt_tokens: 618,
    completion_tokens: 142,
    total_tokens: 760,
    latency_ms: 192,
    cost_usd: 0.0034,
    fallback_triggered: false,
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner Notice */}
      {notification && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/60 text-xs text-blue-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            {notification}
          </span>
          <button onClick={() => setNotification(null)} className="text-blue-500 hover:text-blue-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Main Campaign Header & Controls */}
      <FrostedGlassCard className="p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-[var(--text-primary)]">
                {currentCampaign ? currentCampaign.name : 'Outbound Campaigns & Sequences'}
              </h1>
              {currentCampaign && (
                <span
                  className={`px-2.5 py-1 rounded-[10px] text-[10px] font-bold uppercase tracking-wider ${
                    currentCampaign.status === 'RUNNING'
                      ? 'bg-emerald-100 text-emerald-800'
                      : currentCampaign.status === 'PAUSED'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  ● {currentCampaign.status}
                </span>
              )}
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              {currentCampaign
                ? `Objective: ${currentCampaign.objective} • ${currentCampaign.steps?.length || 0} Sequence Steps • Total Leads: ${currentCampaign.total_leads || 0}`
                : 'Section 6 Deterministic State Machine, Business Hours Dispatch & Celery Scheduler'}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {campaigns.length > 1 && (
              <select
                value={selectedCampaignId || ''}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                className="text-xs bg-white/80 border border-slate-200 rounded-[14px] px-3 py-2 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-[var(--accent-glow)]"
              >
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.status})
                  </option>
                ))}
              </select>
            )}

            <SquircleButton
              variant="primary"
              size="sm"
              onClick={() => setIsBuilderOpen(true)}
              className="flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              New Campaign
            </SquircleButton>

            {currentCampaign && currentCampaign.status === 'RUNNING' && (
              <SquircleButton
                variant="outline"
                size="sm"
                onClick={() => handleCampaignAction('pause')}
                disabled={actionLoading}
                className="flex items-center gap-1.5"
              >
                <Pause className="w-3.5 h-3.5 text-amber-600" />
                Pause
              </SquircleButton>
            )}

            {currentCampaign && currentCampaign.status === 'PAUSED' && (
              <SquircleButton
                variant="primary"
                size="sm"
                onClick={() => handleCampaignAction('resume')}
                disabled={actionLoading}
                className="flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                Resume
              </SquircleButton>
            )}

            {currentCampaign && currentCampaign.status === 'DRAFT' && (
              <SquircleButton
                variant="primary"
                size="sm"
                onClick={() => handleCampaignAction('start')}
                disabled={actionLoading}
                className="flex items-center gap-1.5 shadow-sm"
              >
                <Play className="w-3.5 h-3.5" />
                Launch Campaign
              </SquircleButton>
            )}
          </div>
        </div>
      </FrostedGlassCard>

      {/* Loading state */}
      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Loading Campaign Sequences...</div>
          <div className="text-xs text-[var(--text-muted)]">Querying state machine and lead execution schedules</div>
        </FrostedGlassCard>
      ) : campaigns.length === 0 ? (
        /* Pristine 3D Frosted Glass Empty State */
        <FrostedGlassCard elevated className="p-12 md:p-16 flex flex-col items-center justify-center text-center space-y-5">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Layers className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              No Campaign Sequences Configured
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Design your first multi-step autonomous SDR outreach sequence with deterministic timing delays, AI personalization instructions, and safety stop rules.
            </p>
          </div>
          <SquircleButton
            variant="primary"
            size="md"
            onClick={() => setIsBuilderOpen(true)}
            className="flex items-center gap-2 shadow-md"
          >
            <Plus className="w-4 h-4" />
            Create Your First Campaign
          </SquircleButton>
        </FrostedGlassCard>
      ) : (
        /* Render Active Campaign Details */
        currentCampaign && (
          <div className="space-y-6">
            {/* Step Sequence Pipeline */}
            <FrostedGlassCard className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[var(--accent-primary)]" />
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Active Sequence Progression Steps ({currentCampaign.steps?.length || 0} Steps)
                  </h3>
                </div>
                <span className="text-[11px] text-[var(--text-muted)]">
                  Enforces business-hour window (Mon–Fri, 9:00 AM – 5:00 PM local)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(currentCampaign.steps || []).map((step, idx) => (
                  <div
                    key={step.id || idx}
                    className="p-4 rounded-[18px] bg-white/70 border border-white/80 shadow-xs space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold px-2 py-0.5 rounded-[8px] bg-[var(--accent-subtle)] text-[var(--accent-primary)]">
                        Step {step.step_number}
                      </span>
                      <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {step.delay_days === 0 && step.delay_hours === 0
                          ? 'Immediate send'
                          : `+${step.delay_days}d ${step.delay_hours}h delay`}
                      </span>
                    </div>

                    <p className="text-xs font-semibold text-slate-800 truncate">
                      {step.template_subject || step.template_config_json?.subject || 'Outbound outreach email'}
                    </p>

                    <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                      {step.prompt_instructions || 'Personalize based on lead company pain points.'}
                    </p>
                  </div>
                ))}
              </div>
            </FrostedGlassCard>

            {/* Campaign Leads & Enrolled Prospects */}
            <FrostedGlassCard elevated className="p-0 overflow-hidden">
              <div className="p-4 border-b border-white/60 bg-white/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-[var(--accent-primary)]" />
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Enrolled Prospects ({leads.length})
                  </h3>
                </div>
                <div className="text-xs text-[var(--text-muted)]">
                  Per-lead state machine tracks individual sequence step progression
                </div>
              </div>

              {leads.length === 0 ? (
                <div className="p-8 text-center text-xs text-[var(--text-secondary)]">
                  No prospects enrolled in this campaign yet. Prospects can be enrolled from the Leads view.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-white/60 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] bg-white/20">
                        <th className="py-3 px-6">Prospect</th>
                        <th className="py-3 px-6">Company</th>
                        <th className="py-3 px-6">Timezone</th>
                        <th className="py-3 px-6 text-center">Current Step</th>
                        <th className="py-3 px-6 text-center">State</th>
                        <th className="py-3 px-6 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/60">
                      {leads.map((l) => (
                        <tr key={l.id} className="hover:bg-white/40 transition-colors">
                          <td className="py-3 px-6">
                            <div className="font-semibold text-[var(--text-primary)]">{l.lead_name}</div>
                            <div className="text-xs text-[var(--text-muted)]">{l.email}</div>
                          </td>
                          <td className="py-3 px-6 text-xs text-[var(--text-secondary)]">{l.company_name}</td>
                          <td className="py-3 px-6 text-xs text-slate-500">{l.timezone}</td>
                          <td className="py-3 px-6 text-center">
                            <span className="px-2 py-0.5 rounded-[8px] bg-slate-100 text-slate-700 text-xs font-bold">
                              Step {l.current_step}
                            </span>
                          </td>
                          <td className="py-3 px-6 text-center">
                            <span
                              className={`px-2.5 py-1 rounded-[10px] text-[10px] font-bold ${
                                l.state === 'SENT'
                                  ? 'bg-blue-50 text-blue-700'
                                  : l.state === 'REPLIED'
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : l.state === 'UNSUBSCRIBED'
                                  ? 'bg-rose-50 text-rose-700'
                                  : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              {l.state}
                            </span>
                          </td>
                          <td className="py-3 px-6 text-right">
                            <button
                              onClick={() => {
                                setSelectedLeadForPreview(l);
                                setIsAiModalOpen(true);
                              }}
                              className="text-xs text-[var(--accent-primary)] hover:underline font-semibold"
                            >
                              Inspect AI Draft
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </FrostedGlassCard>

            {/* 5-Question Audit Event Stream */}
            <FrostedGlassCard elevated className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Real-Time 5-Question Audit Trail
                  </h3>
                </div>
                <span className="text-[11px] text-[var(--text-muted)]">
                  Section 19: Immutable logging of model, rules, and state changes
                </span>
              </div>

              {auditEvents.length === 0 ? (
                <div className="p-6 rounded-[16px] bg-slate-50/50 border border-slate-200/50 text-center text-xs text-slate-500">
                  No execution audit events recorded yet for this campaign.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {auditEvents.map((evt) => (
                    <div
                      key={evt.id}
                      className="p-3 rounded-[14px] bg-white/70 border border-white/80 text-xs flex flex-col md:flex-row md:items-center justify-between gap-2"
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-800 flex items-center gap-2">
                          <span className="px-1.5 py-0.5 rounded-[6px] bg-blue-50 text-blue-700 text-[10px] font-mono">
                            {evt.event_type}
                          </span>
                          <span>{evt.lead_email}</span>
                        </div>
                        <p className="text-[11px] text-slate-500">
                          Rule: <span className="font-mono text-slate-700">{evt.rule_matched}</span> • {evt.reason}
                        </p>
                      </div>
                      <div className="text-[11px] text-right text-slate-400 shrink-0 font-mono">
                        {new Date(evt.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </FrostedGlassCard>
          </div>
        )
      )}

      {/* Campaign Builder Wizard Modal */}
      <SquircleModal
        isOpen={isBuilderOpen}
        onClose={() => setIsBuilderOpen(false)}
        title="Autonomous Campaign Builder"
        maxWidth="4xl"
      >
        <CampaignBuilderWizard
          onClose={() => setIsBuilderOpen(false)}
          onSuccess={() => {
            fetchCampaigns();
            setIsBuilderOpen(false);
          }}
        />
      </SquircleModal>

      {/* AI Personalization Modal */}
      <AIPersonalizationModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        leadName={selectedLeadForPreview?.lead_name || 'Selected Prospect'}
        leadCompany={selectedLeadForPreview?.company_name || 'Enterprise Account'}
        draft={sampleDraft}
        telemetry={sampleTelemetry}
      />
    </div>
  );
};
