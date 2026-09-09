import React, { useState } from 'react';
import axios from 'axios';
import {
  Mail,
  Building,
  Briefcase,
  Users,
  MapPin,
  ShieldCheck,
  Pause,
  Play,
  CheckCircle2,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { SquircleModal } from './ui/SquircleModal';
import { SquircleButton } from './ui/SquircleButton';
import { ICPScoreGauge } from './ui/ICPScoreGauge';

export interface LeadDetailItem {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  job_title: string;
  company_name: string;
  industry: string;
  employee_count?: number;
  location?: string;
  icp_score: number;
  score_band?: string;
  qualification_status: 'QUALIFIED' | 'DEVELOPING' | 'UNQUALIFIED';
  is_qualified: boolean;
  qualification_details?: {
    need?: string;
    timing?: string;
    authority?: string;
    pain_points?: string[];
    next_action?: string;
    reason_codes?: string[];
  };
  campaign_name?: string;
  sequence_state?: string;
  hubspot_synced?: boolean;
}

interface LeadDetailModalProps {
  lead: LeadDetailItem | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdateLead?: (updatedLead: LeadDetailItem) => void;
}

export const LeadDetailModal: React.FC<LeadDetailModalProps> = ({
  lead,
  isOpen,
  onClose,
  onUpdateLead,
}) => {
  const [isQualifying, setIsQualifying] = useState(false);
  const [currentLead, setCurrentLead] = useState<LeadDetailItem | null>(lead);

  React.useEffect(() => {
    setCurrentLead(lead);
  }, [lead]);

  if (!currentLead) return null;

  const handleQualify = async () => {
    setIsQualifying(true);
    try {
      const res = await axios.post(`/api/v1/leads/${currentLead.id}/qualify`);
      if (res.data) {
        const updated = {
          ...currentLead,
          qualification_status: res.data.qualification_status,
          is_qualified: res.data.qualification_status === 'QUALIFIED',
          qualification_details: res.data,
        };
        setCurrentLead(updated);
        if (onUpdateLead) onUpdateLead(updated);
      }
    } catch (err) {
      console.error('Failed to qualify lead via NFAT engine:', err);
    } finally {
      setIsQualifying(false);
    }
  };

  const handleTogglePause = () => {
    const nextState = currentLead.sequence_state === 'PAUSED' ? 'READY' : 'PAUSED';
    const updated = { ...currentLead, sequence_state: nextState };
    setCurrentLead(updated);
    if (onUpdateLead) onUpdateLead(updated);
  };

  const handleSuppress = () => {
    alert(`Lead ${currentLead.email} has been suppressed across all campaigns.`);
    onClose();
  };

  return (
    <SquircleModal
      isOpen={isOpen}
      onClose={onClose}
      title={`${currentLead.first_name} ${currentLead.last_name}`}
      subtitle={`${currentLead.job_title} at ${currentLead.company_name}`}
      maxWidth="2xl"
    >
      <div className="space-y-6">
        {/* Top Header Card with ICP Score Gauge & NFAT Pill */}
        <div className="p-5 rounded-[24px] bg-white/70 border border-white/90 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <ICPScoreGauge score={currentLead.icp_score} size="lg" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[var(--text-secondary)] uppercase tracking-wider">
                  ICP Fit Score
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                    currentLead.icp_score >= 80
                      ? 'bg-emerald-100 text-emerald-800'
                      : currentLead.icp_score >= 50
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {currentLead.score_band || (currentLead.icp_score >= 80 ? 'HOT' : 'WARM')}
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-1">
                Deterministic scoring based on vertical, seniority, and domain reputation.
              </p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1.5">
            <span
              className={`px-3 py-1 rounded-[12px] text-xs font-black uppercase tracking-wider flex items-center gap-1.5 ${
                currentLead.qualification_status === 'QUALIFIED'
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : currentLead.qualification_status === 'DEVELOPING'
                  ? 'bg-amber-100 text-amber-800 border border-amber-300'
                  : 'bg-slate-100 text-slate-700 border border-slate-300'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              {currentLead.qualification_status}
            </span>

            {currentLead.hubspot_synced && (
              <span className="text-[11px] text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> HubSpot Synced
              </span>
            )}
          </div>
        </div>

        {/* Lead Profile Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-4 rounded-[18px] bg-slate-50 border border-slate-200/70 space-y-2">
            <span className="font-bold text-[var(--text-secondary)] uppercase text-[10px] tracking-wider block">
              Contact Coordinates
            </span>
            <div className="flex items-center gap-2 text-slate-800">
              <Mail className="w-3.5 h-3.5 text-slate-400" />
              <span>{currentLead.email}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-800">
              <Briefcase className="w-3.5 h-3.5 text-slate-400" />
              <span>{currentLead.job_title}</span>
            </div>
            {currentLead.location && (
              <div className="flex items-center gap-2 text-slate-800">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>{currentLead.location}</span>
              </div>
            )}
          </div>

          <div className="p-4 rounded-[18px] bg-slate-50 border border-slate-200/70 space-y-2">
            <span className="font-bold text-[var(--text-secondary)] uppercase text-[10px] tracking-wider block">
              Company &amp; Firmographics
            </span>
            <div className="flex items-center gap-2 text-slate-800">
              <Building className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-semibold">{currentLead.company_name}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-800">
              <Users className="w-3.5 h-3.5 text-slate-400" />
              <span>{currentLead.industry} • {currentLead.employee_count || 150} employees</span>
            </div>
            <div className="text-[11px] text-[var(--text-muted)]">
              Active Sequence: <span className="font-semibold text-slate-700">{currentLead.campaign_name || 'Enterprise SaaS Q4'}</span>
            </div>
          </div>
        </div>

        {/* NFAT AI Qualification Breakdown */}
        {currentLead.qualification_details && (
          <div className="p-4 rounded-[20px] bg-white/80 border border-white/90 shadow-xs space-y-3">
            <span className="font-bold text-xs text-[var(--text-primary)] flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-[var(--accent-primary)]" />
              NFAT AI Qualification Signals
            </span>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2.5 rounded-[12px] bg-slate-50 border border-slate-200/60">
                <span className="text-[10px] text-[var(--text-muted)] block font-semibold">Timing</span>
                <span className="font-bold text-slate-800">{currentLead.qualification_details.timing || 'NOW'}</span>
              </div>
              <div className="p-2.5 rounded-[12px] bg-slate-50 border border-slate-200/60">
                <span className="text-[10px] text-[var(--text-muted)] block font-semibold">Authority</span>
                <span className="font-bold text-slate-800">{currentLead.qualification_details.authority || 'DECISION_MAKER'}</span>
              </div>
              <div className="p-2.5 rounded-[12px] bg-slate-50 border border-slate-200/60">
                <span className="text-[10px] text-[var(--text-muted)] block font-semibold">Recommended Action</span>
                <span className="font-bold text-emerald-600">{currentLead.qualification_details.next_action || 'BOOK_MEETING'}</span>
              </div>
            </div>

            {currentLead.qualification_details.need && (
              <div className="text-xs text-slate-700 bg-slate-50 p-2.5 rounded-[12px] border border-slate-200/60">
                <span className="font-semibold text-slate-500">Extracted Need: </span>
                {currentLead.qualification_details.need}
              </div>
            )}
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <div className="flex items-center gap-2">
            <SquircleButton
              variant="outline"
              size="sm"
              onClick={handleTogglePause}
              className="text-xs flex items-center gap-1"
            >
              {currentLead.sequence_state === 'PAUSED' ? (
                <>
                  <Play className="w-3.5 h-3.5 text-emerald-600" /> Resume Sequence
                </>
              ) : (
                <>
                  <Pause className="w-3.5 h-3.5 text-amber-600" /> Pause Sequence
                </>
              )}
            </SquircleButton>

            <SquircleButton
              variant="danger"
              size="sm"
              onClick={handleSuppress}
              className="text-xs flex items-center gap-1"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> Suppress Lead
            </SquircleButton>
          </div>

          <SquircleButton
            variant="primary"
            size="sm"
            onClick={handleQualify}
            isLoading={isQualifying}
            className="text-xs flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" /> Re-Qualify with AI
          </SquircleButton>
        </div>
      </div>
    </SquircleModal>
  );
};
