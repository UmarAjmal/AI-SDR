import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Users,
  Plus,
  RefreshCw,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput, SquircleTextarea } from './ui/SquircleInput';
import { SquircleModal } from './ui/SquircleModal';
import { ICPScoreGauge } from './ui/ICPScoreGauge';

export interface QualificationDetails {
  need?: string;
  fit_score?: number;
  authority?: string;
  timing?: string;
  reason?: string;
  pain_points?: string[];
  next_action?: string;
}

export interface LeadItem {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  job_title: string;
  company_name: string;
  domain: string;
  industry: string;
  employee_count?: number;
  total_score: number;
  score_band: 'HOT' | 'WARM' | 'COLD';
  opt_out: boolean;
  lifecycle_stage: string;
  qualification_status: 'QUALIFIED' | 'DEVELOPING' | 'UNQUALIFIED';
  is_qualified: boolean;
  qualification_details?: QualificationDetails;
  reasons: { category: string; points: number; reason: string }[];
}

export const LeadsView: React.FC = () => {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [activeBandFilter, setActiveBandFilter] = useState<'ALL' | 'HOT' | 'WARM' | 'COLD'>('ALL');
  const [activeQualFilter, setActiveQualFilter] = useState<'ALL' | 'QUALIFIED' | 'DEVELOPING' | 'UNQUALIFIED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected lead for detail preview
  const [selectedLead, setSelectedLead] = useState<LeadItem | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  // Add Lead Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    jobTitle: '',
    companyName: '',
    domain: '',
    industry: '',
    employeeCount: '',
    leadNotes: '',
  });

  // Fetch real canonical leads from API
  const fetchLeads = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { page: 1, page_size: 50 };
      if (activeBandFilter !== 'ALL') params.score_band = activeBandFilter;
      if (activeQualFilter !== 'ALL') params.qualification_status = activeQualFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await axios.get('/api/v1/leads', { params });
      const rawItems = res.data?.items || [];

      const mapped: LeadItem[] = rawItems.map((l: any) => ({
        id: l.id,
        first_name: l.first_name || '',
        last_name: l.last_name || '',
        email: l.email || '',
        phone: l.phone || '',
        job_title: l.job_title || 'N/A',
        company_name: l.company_name || 'Unknown Company',
        domain: l.domain || '',
        industry: l.industry || 'General',
        employee_count: l.employee_count,
        total_score: Number(l.total_score || l.icp_score || 0),
        score_band: (l.score_band as any) || (l.total_score >= 80 ? 'HOT' : l.total_score >= 50 ? 'WARM' : 'COLD'),
        opt_out: Boolean(l.opt_out),
        lifecycle_stage: l.lifecycle_stage || 'lead',
        qualification_status: (l.qualification_status as any) || 'UNQUALIFIED',
        is_qualified: Boolean(l.is_qualified),
        qualification_details: l.qualification_details,
        reasons: Array.isArray(l.reasons) ? l.reasons : [],
      }));

      setLeads(mapped);
    } catch (err: any) {
      console.error('Failed to load canonical leads:', err);
      setError(err.response?.data?.detail || 'Unable to connect to lead intelligence service.');
    } finally {
      setIsLoading(false);
    }
  }, [activeBandFilter, activeQualFilter, searchQuery]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Handle manual lead creation with deterministic ICP scoring
  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.email.trim() || !formData.companyName.trim()) {
      setFormError('Work email and company name are strictly required.');
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const payload = {
        first_name: formData.firstName.trim() || undefined,
        last_name: formData.lastName.trim() || undefined,
        email: formData.email.trim().toLowerCase(),
        phone: formData.phone.trim() || undefined,
        job_title: formData.jobTitle.trim() || undefined,
        company_name: formData.companyName.trim(),
        domain: formData.domain.trim() || undefined,
        industry: formData.industry.trim() || undefined,
        employee_count: formData.employeeCount ? parseInt(formData.employeeCount, 10) : undefined,
        lead_notes: formData.leadNotes.trim() || undefined,
      };

      await axios.post('/api/v1/leads', payload);

      // Reset form
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        phone: '',
        jobTitle: '',
        companyName: '',
        domain: '',
        industry: '',
        employeeCount: '',
        leadNotes: '',
      });
      setIsAddModalOpen(false);

      // Refresh real leads list
      await fetchLeads();
    } catch (err: any) {
      console.error('Lead creation error:', err);
      setFormError(err.response?.data?.detail || 'Failed to persist new lead.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Trigger CRM Sync
  const handleTriggerSync = async () => {
    setIsSyncing(true);
    setSyncNotice(null);
    try {
      await axios.post('/api/v1/crm/sync');
      setSyncNotice('CRM sync task initiated in background. Refreshing leads...');
      setTimeout(() => {
        fetchLeads();
        setSyncNotice(null);
      }, 2000);
    } catch (err: any) {
      setSyncNotice(err.response?.data?.detail || 'CRM not connected. You can add leads manually.');
      setTimeout(() => setSyncNotice(null), 4000);
    } finally {
      setIsSyncing(false);
    }
  };

  // Toggle Opt-Out / Do-Not-Contact Stop Condition
  const handleToggleOptOut = async (id: string, currentOptOut: boolean) => {
    try {
      await axios.put(`/api/v1/leads/${id}`, { opt_out: !currentOptOut });
      setLeads((prev) =>
        prev.map((l) => (l.id === id ? { ...l, opt_out: !currentOptOut } : l))
      );
      if (selectedLead && selectedLead.id === id) {
        setSelectedLead((prev) => (prev ? { ...prev, opt_out: !currentOptOut } : null));
      }
    } catch (err) {
      console.error('Failed to toggle opt out:', err);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight flex items-center gap-2">
            Canonical Lead Intelligence
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)]">
              Deterministic 0–100 ICP Scored
            </span>
          </h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Section 5 CRM Integration &amp; Section 9 NFAT AI Qualification Engine with Bi-directional Sync.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <SquircleButton
            variant="outline"
            size="sm"
            onClick={handleTriggerSync}
            disabled={isSyncing}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Syncing...' : 'Sync CRM Leads'}
          </SquircleButton>

          <SquircleButton
            variant="primary"
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add New Lead
          </SquircleButton>
        </div>
      </div>

      {/* Sync Status Banner */}
      {syncNotice && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/60 text-xs text-blue-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            {syncNotice}
          </span>
          <button onClick={() => setSyncNotice(null)} className="text-blue-500 hover:text-blue-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Error Status Banner */}
      {error && (
        <FrostedGlassCard className="p-3.5 border-rose-200/80 bg-rose-50/60 text-xs text-rose-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Filter and Search Bar */}
      <FrostedGlassCard className="p-4 flex flex-col lg:flex-row items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          {/* Score Band Filter */}
          <div className="flex items-center gap-1.5 p-1 bg-white/60 backdrop-blur-md rounded-[16px] border border-white/80">
            {(['ALL', 'HOT', 'WARM', 'COLD'] as const).map((band) => (
              <button
                key={band}
                onClick={() => setActiveBandFilter(band)}
                className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all ${
                  activeBandFilter === band
                    ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {band}
              </button>
            ))}
          </div>

          {/* NFAT Qualification Filter */}
          <div className="flex items-center gap-1.5 p-1 bg-white/60 backdrop-blur-md rounded-[16px] border border-white/80">
            {(['ALL', 'QUALIFIED', 'DEVELOPING', 'UNQUALIFIED'] as const).map((qual) => (
              <button
                key={qual}
                onClick={() => setActiveQualFilter(qual)}
                className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold transition-all ${
                  activeQualFilter === qual
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {qual === 'QUALIFIED' ? '★ Qualified' : qual}
              </button>
            ))}
          </div>
        </div>

        <div className="w-full lg:w-72 relative">
          <SquircleInput
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search leads, companies..."
          />
        </div>
      </FrostedGlassCard>

      {/* Leads Table or Pristine Empty State */}
      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Connecting to Lead Intelligence Database...</div>
          <div className="text-xs text-[var(--text-muted)]">Computing ICP scores and syncing CRM metadata</div>
        </FrostedGlassCard>
      ) : leads.length === 0 ? (
        /* Pristine 3D Frosted Glass Empty State */
        <FrostedGlassCard elevated className="p-12 md:p-16 flex flex-col items-center justify-center text-center space-y-5">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Users className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              No Canonical Leads in Workspace
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Enter your target prospect details manually or connect HubSpot CRM in Integrations to import leads with automatic deterministic 0–100 ICP scoring.
            </p>
          </div>
          <SquircleButton
            variant="primary"
            size="md"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 shadow-md"
          >
            <Plus className="w-4 h-4" />
            Add Your First Lead
          </SquircleButton>
        </FrostedGlassCard>
      ) : (
        /* Dynamic Leads Table */
        <FrostedGlassCard elevated className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b border-white/60 bg-white/40 text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                  <th className="py-3.5 px-6">Lead / Contact</th>
                  <th className="py-3.5 px-6">Company &amp; Domain</th>
                  <th className="py-3.5 px-6">Job Title</th>
                  <th className="py-3.5 px-6 text-center">ICP Score</th>
                  <th className="py-3.5 px-6 text-center">NFAT Qualification</th>
                  <th className="py-3.5 px-6 text-center">Status</th>
                  <th className="py-3.5 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/60">
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="hover:bg-white/50 transition-colors duration-150 cursor-pointer"
                    onClick={() => setSelectedLead(lead)}
                  >
                    {/* Lead Info */}
                    <td className="py-4 px-6">
                      <div className="font-semibold text-[var(--text-primary)]">
                        {lead.first_name} {lead.last_name}
                      </div>
                      <div className="text-xs text-[var(--text-muted)] mt-0.5">{lead.email}</div>
                    </td>

                    {/* Company */}
                    <td className="py-4 px-6">
                      <div className="font-medium text-[var(--text-primary)]">{lead.company_name}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs text-[var(--text-muted)]">{lead.domain || 'No domain'}</span>
                        {lead.industry && (
                          <span className="px-2 py-0.5 text-[10px] font-semibold rounded-[6px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)]">
                            {lead.industry}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Title */}
                    <td className="py-4 px-6 text-xs text-[var(--text-secondary)]">
                      {lead.job_title}
                    </td>

                    {/* ICP Score */}
                    <td className="py-4 px-6 text-center" onClick={(e) => e.stopPropagation()}>
                      <ICPScoreGauge
                        score={lead.total_score}
                        scoreBand={lead.score_band}
                        reasons={lead.reasons}
                        size="sm"
                      />
                    </td>

                    {/* NFAT Qualification Status */}
                    <td className="py-4 px-6 text-center">
                      {lead.qualification_status === 'QUALIFIED' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[12px] text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-300 shadow-sm">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                          Qualified
                        </span>
                      ) : lead.qualification_status === 'DEVELOPING' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[12px] text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-300">
                          <span className="w-2 h-2 rounded-full bg-amber-500" />
                          Developing
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[12px] text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-300">
                          <span className="w-2 h-2 rounded-full bg-slate-400" />
                          Unqualified
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="py-4 px-6 text-center">
                      {lead.opt_out ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-[8px] text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
                          Opted Out
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-[8px] text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Active
                        </span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-4 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => handleToggleOptOut(lead.id, lead.opt_out)}
                        className={`text-xs font-medium px-2.5 py-1 rounded-[10px] transition-all ${
                          lead.opt_out
                            ? 'text-slate-600 bg-slate-100 hover:bg-slate-200'
                            : 'text-red-600 hover:bg-red-50'
                        }`}
                      >
                        {lead.opt_out ? 'Un-suppress' : 'Suppress'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </FrostedGlassCard>
      )}

      {/* Interactive "+ Add Lead" Modal */}
      <SquircleModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Canonical Lead"
        maxWidth="xl"
      >
        <form onSubmit={handleCreateLead} className="space-y-4 pt-1">
          {formError && (
            <div className="p-3 rounded-[12px] bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <SquircleInput
              label="First Name"
              value={formData.firstName}
              onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
              placeholder="e.g. Marcus"
            />
            <SquircleInput
              label="Last Name"
              value={formData.lastName}
              onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
              placeholder="e.g. Vance"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <SquircleInput
              label="Work Email *"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="marcus@company.com"
            />
            <SquircleInput
              label="Phone Number"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+1 (555) 019-2834"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <SquircleInput
              label="Job Title"
              value={formData.jobTitle}
              onChange={(e) => setFormData({ ...formData, jobTitle: e.target.value })}
              placeholder="VP of Revenue Operations"
            />
            <SquircleInput
              label="Company Name *"
              required
              value={formData.companyName}
              onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
              placeholder="Acme Corp"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <SquircleInput
              label="Domain"
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              placeholder="acme.io"
            />
            <SquircleInput
              label="Industry"
              value={formData.industry}
              onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
              placeholder="SaaS / FinTech"
            />
            <SquircleInput
              label="Employees"
              type="number"
              value={formData.employeeCount}
              onChange={(e) => setFormData({ ...formData, employeeCount: e.target.value })}
              placeholder="250"
            />
          </div>

          <SquircleTextarea
            label="Lead Context & Notes"
            rows={2}
            value={formData.leadNotes}
            onChange={(e) => setFormData({ ...formData, leadNotes: e.target.value })}
            placeholder="Key initiatives, current pain points, tech stack notes..."
          />

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsAddModalOpen(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isSubmitting}
            >
              Save &amp; Compute ICP Score
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>

      {/* Lead Detail Slide-Over / Modal */}
      {selectedLead && (
        <SquircleModal
          isOpen={!!selectedLead}
          onClose={() => setSelectedLead(null)}
          title={`Lead Profile: ${selectedLead.first_name} ${selectedLead.last_name}`}
          maxWidth="2xl"
        >
          <div className="space-y-6 pt-2">
            {/* Top Identity Card */}
            <div className="flex items-center justify-between p-4 rounded-[18px] bg-slate-50 border border-slate-200/80">
              <div>
                <h4 className="text-base font-bold text-[var(--text-primary)]">
                  {selectedLead.first_name} {selectedLead.last_name}
                </h4>
                <p className="text-xs text-[var(--text-secondary)]">{selectedLead.job_title} at {selectedLead.company_name}</p>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">{selectedLead.email}</p>
              </div>
              <ICPScoreGauge
                score={selectedLead.total_score}
                scoreBand={selectedLead.score_band}
                reasons={selectedLead.reasons}
                size="md"
              />
            </div>

            {/* Score Reason Breakdown */}
            <div>
              <h5 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] mb-2">
                Explainable ICP Scoring Reasons
              </h5>
              <div className="space-y-1.5">
                {selectedLead.reasons && selectedLead.reasons.length > 0 ? (
                  selectedLead.reasons.map((r, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-[12px] bg-white border border-slate-200/70 text-xs flex items-center justify-between"
                    >
                      <span className="text-[var(--text-secondary)]">{r.reason}</span>
                      <span
                        className={`font-bold ${
                          r.points >= 0 ? 'text-emerald-600' : 'text-rose-600'
                        }`}
                      >
                        {r.points > 0 ? `+${r.points}` : r.points} pts
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-[var(--text-muted)] italic">
                    Base score evaluated against target ICP parameters.
                  </p>
                )}
              </div>
            </div>

            {/* Action Bar */}
            <div className="pt-2 flex items-center justify-between border-t border-slate-200">
              <SquircleButton
                variant={selectedLead.opt_out ? 'outline' : 'danger'}
                size="sm"
                onClick={() => handleToggleOptOut(selectedLead.id, selectedLead.opt_out)}
              >
                {selectedLead.opt_out ? 'Remove Global Suppression' : 'Suppress Lead (Opt-Out)'}
              </SquircleButton>

              <SquircleButton
                variant="outline"
                size="sm"
                onClick={() => setSelectedLead(null)}
              >
                Close
              </SquircleButton>
            </div>
          </div>
        </SquircleModal>
      )}
    </div>
  );
};
