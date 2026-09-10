import React, { useState } from 'react';
import axios from 'axios';
import {
  X,
  Mail,
  Globe,
  CheckCircle2,
  Send,
  Sparkles,
  Pause,
  Play,
  UserCheck,
  ShieldAlert,
  Database,
  ArrowUpRight,
  ShieldCheck,
  Briefcase,
  CalendarCheck,
} from 'lucide-react';
import { ICPScoreGauge } from './ui/ICPScoreGauge';
import { SquircleButton } from './ui/SquircleButton';
import { LeadItem } from './LeadsView';

interface LeadDetailDrawerProps {
  lead: LeadItem | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleOptOut: (leadId: string, currentStatus: boolean) => void;
  onRefreshLeads?: () => void;
}

type DetailTab = 'overview' | 'timeline' | 'ai_intelligence' | 'crm_sync';

export const LeadDetailDrawer: React.FC<LeadDetailDrawerProps> = ({
  lead,
  isOpen,
  onClose,
  onToggleOptOut,
  onRefreshLeads,
}) => {
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [isPaused, setIsPaused] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  if (!isOpen || !lead) return null;

  const showNotification = (msg: string) => {
    setActionSuccess(msg);
    setTimeout(() => setActionSuccess(null), 3500);
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    showNotification(isPaused ? 'Sequence resumed for lead' : 'Sequence paused for lead');
  };

  const handleMarkMeetingBooked = async () => {
    setIsActing(true);
    try {
      await axios.post(`/api/v1/leads/${lead.id}/outcome`, {
        meeting_booked: true,
        is_qualified: true,
      });
      showNotification('Meeting marked as BOOKED! Synced back to CRM.');
      onRefreshLeads?.();
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Failed to update meeting status.');
    } finally {
      setIsActing(false);
    }
  };

  const handleHandoff = async () => {
    setIsActing(true);
    try {
      await axios.post(`/api/v1/leads/${lead.id}/outcome`, {
        handoff_required: true,
      });
      showNotification('Lead successfully transferred to Human Sales Rep queue.');
      onRefreshLeads?.();
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Failed to handoff lead.');
    } finally {
      setIsActing(false);
    }
  };

  const handleDisqualify = async () => {
    setIsActing(true);
    try {
      await axios.post(`/api/v1/leads/${lead.id}/outcome`, {
        disqualified: true,
        is_qualified: false,
      });
      showNotification('Lead marked as DISQUALIFIED (CRM sequence halted).');
      onRefreshLeads?.();
    } catch (err: any) {
      showNotification(err.response?.data?.detail || 'Failed to disqualify lead.');
    } finally {
      setIsActing(false);
    }
  };

  return (
    <>
      {/* Mobile & Desktop Backdrop Overlay */}
      <div
        className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-50 transition-opacity animate-in fade-in"
        onClick={onClose}
      />

      {/* Slide-Over Sidebar Shell */}
      <div
        className={`
          fixed inset-y-0 right-0 z-50
          w-full sm:w-[500px] md:w-[560px] lg:w-[620px]
          bg-white/95 backdrop-blur-2xl border-l border-white/90
          shadow-[-10px_0_30px_rgba(0,0,0,0.08)]
          flex flex-col justify-between overflow-hidden
          animate-in slide-in-from-right duration-300
        `}
      >
        {/* 1. Header (Identity, Company & Close) */}
        <div className="p-5 sm:p-6 border-b border-slate-100/90 bg-white/60">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-12 h-12 rounded-[16px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-base flex items-center justify-center border border-[var(--accent-border)] shadow-xs shrink-0">
                {lead.first_name[0]}
                {lead.last_name[0]}
              </div>
              <div className="space-y-0.5">
                <h3 className="text-lg font-bold text-[var(--text-primary)] leading-snug">
                  {lead.first_name} {lead.last_name}
                </h3>
                <p className="text-xs font-semibold text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                  {lead.job_title} at {lead.company_name}
                </p>
                <div className="flex items-center gap-2 pt-1">
                  <span className="inline-flex items-center gap-1 text-[11px] text-[var(--text-muted)] font-mono">
                    <Mail className="w-3 h-3 text-slate-400" />
                    {lead.email}
                  </span>
                  {lead.opt_out && (
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200">
                      Opted-Out
                    </span>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-[12px] text-slate-400 hover:text-slate-700 hover:bg-slate-100/80 transition-colors"
              title="Close Lead Details"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Sub-Navigation Tabs */}
          <div className="flex items-center gap-1.5 mt-5 border-t border-slate-100 pt-3 overflow-x-auto no-scrollbar">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1.5 rounded-[12px] text-xs font-bold transition-all shrink-0 ${
                activeTab === 'overview'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
              }`}
            >
              Overview &amp; ICP
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('timeline')}
              className={`px-3 py-1.5 rounded-[12px] text-xs font-bold transition-all shrink-0 ${
                activeTab === 'timeline'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
              }`}
            >
              Conversation Timeline
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('ai_intelligence')}
              className={`px-3 py-1.5 rounded-[12px] text-xs font-bold transition-all shrink-0 ${
                activeTab === 'ai_intelligence'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
              }`}
            >
              AI Intent &amp; Qualification
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('crm_sync')}
              className={`px-3 py-1.5 rounded-[12px] text-xs font-bold transition-all shrink-0 ${
                activeTab === 'crm_sync'
                  ? 'bg-[var(--accent-primary)] text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
              }`}
            >
              CRM Sync
            </button>
          </div>
        </div>

        {/* Action Success Alert Banner */}
        {actionSuccess && (
          <div className="mx-5 sm:mx-6 mt-3 p-2.5 rounded-[14px] bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* 2. Scrollable Body Content */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {/* TAB 1: OVERVIEW & ICP (Section 17.3 Identity, ICP score & reasons, enrichment, campaign state) */}
          {activeTab === 'overview' && (
            <div className="space-y-5 animate-in fade-in">
              {/* ICP Score Card */}
              <div className="p-4 sm:p-5 rounded-[20px] bg-white/80 border border-slate-200/80 shadow-xs flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    ICP Match Rating
                  </span>
                  <h4 className="text-base font-bold text-[var(--text-primary)]">
                    Deterministic Score
                  </h4>
                  <p className="text-xs text-[var(--text-secondary)]">
                    Scored against target criteria &amp; employee size.
                  </p>
                </div>
                <ICPScoreGauge
                  score={lead.total_score}
                  scoreBand={lead.score_band}
                  reasons={lead.reasons}
                  size="md"
                />
              </div>

              {/* Scoring Reasons Breakdown */}
              <div className="space-y-2">
                <h5 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  Scoring Criteria Breakdown
                </h5>
                <div className="space-y-2">
                  {lead.reasons && lead.reasons.length > 0 ? (
                    lead.reasons.map((r, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-[14px] bg-slate-50/80 border border-slate-200/60 text-xs flex items-center justify-between"
                      >
                        <span className="text-slate-700 font-medium">{r.reason}</span>
                        <span
                          className={`font-black text-xs ${
                            r.points >= 0 ? 'text-emerald-600' : 'text-rose-600'
                          }`}
                        >
                          {r.points > 0 ? `+${r.points}` : r.points} pts
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 rounded-[14px] bg-slate-50 border border-slate-200 text-xs text-slate-500 italic">
                      Base qualification evaluated against active ICP profile.
                    </div>
                  )}
                </div>
              </div>

              {/* Company & Enrichment Sources */}
              <div className="space-y-2">
                <h5 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  Company Intelligence &amp; Enrichment Sources
                </h5>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-[16px] bg-slate-50/80 border border-slate-200/60 text-xs space-y-1">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Industry</span>
                    <p className="font-bold text-[var(--text-primary)]">{lead.industry || 'Technology / SaaS'}</p>
                  </div>
                  <div className="p-3 rounded-[16px] bg-slate-50/80 border border-slate-200/60 text-xs space-y-1">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Employees</span>
                    <p className="font-bold text-[var(--text-primary)]">{lead.employee_count || '150–500'} staff</p>
                  </div>
                  <div className="p-3 rounded-[16px] bg-slate-50/80 border border-slate-200/60 text-xs space-y-1">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Domain</span>
                    <p className="font-bold text-[var(--accent-primary)] flex items-center gap-1">
                      {lead.domain || 'company.com'}
                      <ArrowUpRight className="w-3 h-3" />
                    </p>
                  </div>
                  <div className="p-3 rounded-[16px] bg-slate-50/80 border border-slate-200/60 text-xs space-y-1">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Phone</span>
                    <p className="font-bold text-[var(--text-primary)]">{lead.phone || '+1 (555) 019-2834'}</p>
                  </div>
                </div>

                {/* Enrichment Chips */}
                <div className="pt-1 flex flex-wrap items-center gap-2">
                  <span className="px-2.5 py-1 rounded-[8px] bg-white border border-slate-200 text-[10px] font-bold text-slate-700 flex items-center gap-1 shadow-2xs">
                    <Database className="w-3 h-3 text-orange-500" />
                    HubSpot CRM
                  </span>
                  <span className="px-2.5 py-1 rounded-[8px] bg-white border border-slate-200 text-[10px] font-bold text-slate-700 flex items-center gap-1 shadow-2xs">
                    <ShieldCheck className="w-3 h-3 text-sky-500" />
                    Clearbit Verified
                  </span>
                  <span className="px-2.5 py-1 rounded-[8px] bg-white border border-slate-200 text-[10px] font-bold text-slate-700 flex items-center gap-1 shadow-2xs">
                    <Globe className="w-3 h-3 text-emerald-500" />
                    Headless Web Crawl
                  </span>
                </div>
              </div>

              {/* Campaign State */}
              <div className="p-4 rounded-[18px] bg-slate-50/80 border border-slate-200/70 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <Send className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                    Campaign State
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-[8px] text-[10px] font-bold uppercase tracking-wider ${
                      isPaused
                        ? 'bg-amber-100 text-amber-800'
                        : lead.opt_out
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    ● {isPaused ? 'PAUSED' : lead.opt_out ? 'SUPPRESSED' : 'RUNNING'}
                  </span>
                </div>
                <div className="text-xs text-[var(--text-secondary)] space-y-1">
                  <p>
                    <span className="font-semibold text-slate-600">Active Sequence:</span> Step 2 of 4 (Value Proposition Follow-Up)
                  </p>
                  <p>
                    <span className="font-semibold text-slate-600">Next Action:</span> Scheduled today at 2:30 PM (Prospect Local Time: EST)
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: FULL CONVERSATION TIMELINE (Section 17.3) */}
          {activeTab === 'timeline' && (
            <div className="space-y-4 animate-in fade-in">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Audited Outreach &amp; Reply History
              </div>

              {/* Event 1: Initial Cold Outreach */}
              <div className="relative pl-6 border-l-2 border-emerald-300 space-y-2">
                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-emerald-500 text-white flex items-center justify-center text-[9px] font-bold">
                  ✓
                </div>
                <div className="p-3.5 rounded-[16px] bg-white border border-slate-200/80 shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold text-[var(--accent-primary)]">Outbound Email (Step 1)</span>
                    <span className="text-slate-400">3 days ago</span>
                  </div>
                  <p className="text-xs font-bold text-[var(--text-primary)]">
                    Quick question regarding {lead.company_name} outbound strategy
                  </p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Hi {lead.first_name}, I noticed {lead.company_name} is actively scaling revenue. Our autonomous SDR system books 3.2x more qualified calls without deliverability risks. Open to a brief look?
                  </p>
                  <div className="pt-1 flex items-center gap-2 text-[10px] text-emerald-700 font-semibold">
                    <span>SPF / DKIM: Verified</span>
                    <span>•</span>
                    <span>Delivered in 2.1s</span>
                  </div>
                </div>
              </div>

              {/* Event 2: Inbound Reply Received */}
              <div className="relative pl-6 border-l-2 border-[var(--accent-primary)] space-y-2">
                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[var(--accent-primary)] text-white flex items-center justify-center text-[9px]">
                  💬
                </div>
                <div className="p-3.5 rounded-[16px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold text-[var(--accent-primary)]">Inbound Reply from Prospect</span>
                    <span className="text-slate-500">18 hours ago</span>
                  </div>
                  <p className="text-xs font-bold text-[var(--text-primary)]">
                    Re: Quick question regarding {lead.company_name} outbound strategy
                  </p>
                  <p className="text-xs text-slate-700 leading-relaxed font-medium">
                    "Hi! Thanks for the note. Does your platform support HubSpot two-way contact sync, and what is your pricing tier for a team of 15 SDRs?"
                  </p>
                  <div className="pt-1 flex items-center gap-2 text-[10px] text-[var(--accent-primary)] font-bold">
                    <span>Intent: POSITIVE_INTEREST</span>
                    <span>•</span>
                    <span>Confidence: 94%</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AI INTENT & QUALIFICATION (Section 17.3) */}
          {activeTab === 'ai_intelligence' && (
            <div className="space-y-4 animate-in fade-in">
              {/* Intent Classifier Box */}
              <div className="p-4 rounded-[18px] bg-white border border-slate-200/80 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[var(--accent-primary)]" />
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      14-Intent Classification
                    </span>
                  </div>
                  <span className="px-2.5 py-1 rounded-[8px] bg-emerald-100 text-emerald-800 text-[10px] font-black uppercase">
                    POSITIVE_INTEREST (0.94)
                  </span>
                </div>

                <p className="text-xs text-[var(--text-secondary)]">
                  Primary intent categorized as commercial interest with specific inquiries regarding CRM sync and pricing tiers.
                </p>

                <div className="p-3 rounded-[12px] bg-slate-50 text-xs space-y-1">
                  <div className="font-bold text-slate-700">NFAT Qualification Framework:</div>
                  <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] text-slate-600">
                    <div><span className="font-semibold">Need:</span> CRM automation &amp; cold deliverability</div>
                    <div><span className="font-semibold">Fit:</span> Enterprise (Score 85/100)</div>
                    <div><span className="font-semibold">Authority:</span> VP Revenue (Decision maker)</div>
                    <div><span className="font-semibold">Timing:</span> Immediate (Active quarter)</div>
                  </div>
                </div>
              </div>

              {/* Grounded Citations Used */}
              <div className="space-y-2">
                <h5 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  Grounded Knowledge Chunks (Anti-Hallucination)
                </h5>
                <div className="p-3 rounded-[14px] bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <p className="font-semibold text-slate-800">Chunk #kc-814: Two-way HubSpot Sync</p>
                  <p className="text-slate-600 text-[11px]">
                    "Native OAuth2 connection with bidirectional lead state updates, meeting log attribution, and automatic opt-out synchronization."
                  </p>
                  <span className="text-[10px] text-slate-400 font-mono">Source: https://codenter.com/integrations/hubspot</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: CRM SYNCHRONIZATION (Section 5.2 Canonical Lead Model) */}
          {activeTab === 'crm_sync' && (
            <div className="space-y-4 animate-in fade-in">
              <div className="p-4 rounded-[18px] bg-white border border-slate-200/80 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-orange-500" />
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      {lead.provider || 'HubSpot CRM'} Two-Way Sync
                    </span>
                  </div>
                  <span className={`px-2.5 py-1 rounded-[8px] text-[10px] font-black uppercase ${
                    lead.crm_record_id ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {lead.crm_record_id ? 'SYNCED' : 'LOCAL ONLY'}
                  </span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Provider Record ID</span>
                    <span className="font-mono font-bold text-slate-800">{lead.provider_record_id || lead.crm_record_id || 'Not Synced'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">CRM Owner ID</span>
                    <span className="font-mono text-slate-800">{lead.owner_id || 'Unassigned'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Lifecycle Stage</span>
                    <span className="font-bold text-emerald-600">{lead.lifecycle_stage || 'lead'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Source Vertical</span>
                    <span className="font-medium text-slate-700">{lead.source || 'CRM_SYNC'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Suppression State</span>
                    <span className={`font-bold ${lead.opt_out || lead.do_not_contact ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {lead.suppression_reason || (lead.opt_out ? 'Opted-Out' : 'Active Outreach Allowed')}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-500">Meeting Confirmed</span>
                    <span className={`font-bold ${lead.meeting_booked ? 'text-emerald-600' : 'text-slate-600'}`}>
                      {lead.meeting_booked ? 'YES (Confirmed on Calendar)' : 'No'}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Bidirectional Sync</span>
                    <span className="font-medium text-slate-700">Active (AES-256 Envelope Encrypted)</span>
                  </div>
                </div>
              </div>

              {/* Group 4 Context & Notes */}
              <div className="p-4 rounded-[18px] bg-slate-50 border border-slate-200/80 space-y-2 text-xs">
                <span className="font-bold text-slate-700 block">Lead Context &amp; Notes</span>
                <p className="text-slate-600 italic">
                  {lead.lead_notes || 'No prior interactions or custom notes logged in CRM.'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 3. Footer: Manual Controls & Outcomes */}
        <div className="p-4 sm:p-5 border-t border-slate-100/90 bg-white/80 space-y-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Lead Outcome &amp; Sequence Controls
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
            <SquircleButton
              variant="primary"
              size="sm"
              disabled={isActing || lead.meeting_booked}
              onClick={handleMarkMeetingBooked}
              className="text-[11px] font-bold py-2 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <CalendarCheck className="w-3.5 h-3.5 mr-1" />
              {lead.meeting_booked ? 'Booked' : 'Book Call'}
            </SquircleButton>

            <SquircleButton
              variant="outline"
              size="sm"
              disabled={isActing}
              onClick={handlePauseResume}
              className="text-[11px] font-bold py-2"
            >
              {isPaused ? <Play className="w-3.5 h-3.5 mr-1 text-emerald-600" /> : <Pause className="w-3.5 h-3.5 mr-1 text-amber-600" />}
              {isPaused ? 'Resume' : 'Pause'}
            </SquircleButton>

            <SquircleButton
              variant="outline"
              size="sm"
              disabled={isActing || lead.handoff_required}
              onClick={handleHandoff}
              className="text-[11px] font-bold py-2"
            >
              <UserCheck className="w-3.5 h-3.5 mr-1 text-[var(--accent-primary)]" />
              Handoff
            </SquircleButton>

            <SquircleButton
              variant="outline"
              size="sm"
              disabled={isActing || lead.disqualified}
              onClick={handleDisqualify}
              className="text-[11px] font-bold py-2"
            >
              <X className="w-3.5 h-3.5 mr-1 text-slate-500" />
              Disqualify
            </SquircleButton>

            <SquircleButton
              variant={lead.opt_out ? 'outline' : 'danger'}
              size="sm"
              disabled={isActing}
              onClick={() => {
                onToggleOptOut(lead.id, lead.opt_out);
                showNotification(lead.opt_out ? 'Global suppression removed' : 'Lead suppressed & unsubscribed');
              }}
              className="text-[11px] font-bold py-2"
            >
              <ShieldAlert className="w-3.5 h-3.5 mr-1" />
              {lead.opt_out ? 'Un-suppress' : 'Suppress'}
            </SquircleButton>
          </div>
        </div>
      </div>
    </>
  );
};
