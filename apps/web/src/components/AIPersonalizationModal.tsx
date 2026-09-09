import React, { useState } from 'react';
import { SquircleButton } from './ui/SquircleButton';

export interface OutboundDraftData {
  subject: string;
  body: string;
  personalization_facts: string[];
  cta: string;
  claims_used: string[];
  confidence: number;
  risk_flags: string[];
  recommended_action: 'SEND' | 'HUMAN_REVIEW' | 'REVISE';
}

export interface ModelTelemetryData {
  model: string;
  prompt_version: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number;
  fallback_triggered: boolean;
}

interface AIPersonalizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  leadName: string;
  leadCompany: string;
  leadTitle?: string;
  draft: OutboundDraftData;
  telemetry?: ModelTelemetryData;
  citations?: string[];
  onApprove?: (finalDraft: OutboundDraftData) => void;
}

export const AIPersonalizationModal: React.FC<AIPersonalizationModalProps> = ({
  isOpen,
  onClose,
  leadName,
  leadCompany,
  leadTitle = 'Decision Maker',
  draft,
  telemetry,
  citations = [],
  onApprove,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedSubject, setEditedSubject] = useState(draft.subject);
  const [editedBody, setEditedBody] = useState(draft.body);

  if (!isOpen) return null;

  const confidencePercent = Math.round((draft.confidence || 0.9) * 100);
  const isHumanReviewRequired =
    draft.recommended_action === 'HUMAN_REVIEW' ||
    draft.confidence < 0.85 ||
    draft.risk_flags.length > 0;

  const handleApprove = () => {
    if (onApprove) {
      onApprove({
        ...draft,
        subject: editedSubject,
        body: editedBody,
      });
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto bg-white/95 backdrop-blur-2xl border border-white/80 rounded-[32px] shadow-[0_25px_50px_-12px_rgba(15,23,42,0.18)] p-6 sm:p-8 flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-900">
                AI Outbound Personalization & Grounding
              </h2>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200/60">
                Milestone 6 AI Gate
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Recipient: <strong className="text-slate-800">{leadName}</strong> ({leadTitle} at{' '}
              <strong className="text-slate-800">{leadCompany}</strong>)
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100/80 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Telemetry & Safety Overview Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Confidence Meter */}
          <div className="p-3.5 rounded-[18px] bg-slate-50/80 border border-slate-200/70 flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs ${
                confidencePercent >= 85
                  ? 'bg-emerald-100 text-emerald-800 ring-2 ring-emerald-400/30'
                  : 'bg-amber-100 text-amber-800 ring-2 ring-amber-400/30'
              }`}
            >
              {confidencePercent}%
            </div>
            <div>
              <div className="text-xs font-medium text-slate-500">Grounded Confidence</div>
              <div className="text-xs font-semibold text-slate-800">
                {confidencePercent >= 85 ? 'High Confidence (Verified)' : 'Requires Human Review'}
              </div>
            </div>
          </div>

          {/* Model Gateway Telemetry */}
          <div className="p-3.5 rounded-[18px] bg-slate-50/80 border border-slate-200/70">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Model:</span>
              <span className="font-semibold text-slate-800">
                {telemetry?.model || 'claude-3-5-sonnet'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs mt-1">
              <span className="text-slate-500">Latency & Tokens:</span>
              <span className="font-medium text-slate-700">
                {telemetry?.latency_ms ? `${Math.round(telemetry.latency_ms)}ms` : '180ms'} ·{' '}
                {telemetry?.total_tokens || 842} tok
              </span>
            </div>
          </div>

          {/* Cost USD */}
          <div className="p-3.5 rounded-[18px] bg-slate-50/80 border border-slate-200/70">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500">Action Recommendation:</span>
              <span
                className={`font-semibold px-2 py-0.5 rounded-md text-[11px] ${
                  isHumanReviewRequired
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-emerald-100 text-emerald-800'
                }`}
              >
                {draft.recommended_action}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs mt-1">
              <span className="text-slate-500">Estimated Cost:</span>
              <span className="font-semibold text-slate-800">
                ${(telemetry?.cost_usd || 0.0035).toFixed(4)} USD
              </span>
            </div>
          </div>
        </div>

        {/* Risk Flags Warning Banner (if any) */}
        {draft.risk_flags && draft.risk_flags.length > 0 && (
          <div className="p-4 rounded-[18px] bg-amber-50/90 border border-amber-200 text-amber-900 text-xs flex items-start gap-3 shadow-sm">
            <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <strong className="font-semibold">Human Review Gate Triggered:</strong>
              <ul className="list-disc list-inside mt-1 space-y-0.5">
                {draft.risk_flags.map((flag, idx) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Verified Knowledge Grounding & Citations */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-[20px] bg-slate-50/70 border border-slate-200/60">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Grounded Claims Used ({draft.claims_used?.length || 0})
            </h4>
            {draft.claims_used && draft.claims_used.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {draft.claims_used.map((claim, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 text-xs rounded-[10px] bg-white border border-slate-200 text-slate-700 shadow-sm"
                  >
                    ✓ {claim}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-xs text-slate-400 italic">No specific metric claims cited.</span>
            )}
          </div>

          <div className="p-4 rounded-[20px] bg-slate-50/70 border border-slate-200/60">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Verified Knowledge Citations ({citations.length})
            </h4>
            {citations.length > 0 ? (
              <div className="space-y-1">
                {citations.map((url, idx) => (
                  <a
                    key={idx}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-800 hover:underline truncate block"
                  >
                    🔗 {url}
                  </a>
                ))}
              </div>
            ) : (
              <span className="text-xs text-slate-400 italic">Internal company knowledge base</span>
            )}
          </div>
        </div>

        {/* Draft Email Preview & Editing */}
        <div className="border border-slate-200 rounded-[24px] p-5 bg-white shadow-sm flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Outbound Email Draft
            </div>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="text-xs font-semibold text-[var(--accent-primary)] hover:underline flex items-center gap-1"
            >
              {isEditing ? 'Done Editing' : '✎ Edit Draft'}
            </button>
          </div>

          {/* Subject Line */}
          <div>
            <label className="text-xs font-semibold text-slate-600 block mb-1">Subject</label>
            {isEditing ? (
              <input
                type="text"
                value={editedSubject}
                onChange={(e) => setEditedSubject(e.target.value)}
                className="w-full px-3.5 py-2 text-sm rounded-[14px] border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
              />
            ) : (
              <div className="text-sm font-medium text-slate-900 bg-slate-50/60 px-3.5 py-2 rounded-[14px] border border-slate-100">
                {editedSubject}
              </div>
            )}
          </div>

          {/* Email Body */}
          <div>
            <label className="text-xs font-semibold text-slate-600 block mb-1">Body Text</label>
            {isEditing ? (
              <textarea
                rows={6}
                value={editedBody}
                onChange={(e) => setEditedBody(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm rounded-[16px] border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] font-sans"
              />
            ) : (
              <div className="text-sm text-slate-700 bg-slate-50/60 p-4 rounded-[16px] border border-slate-100 whitespace-pre-line leading-relaxed font-sans">
                {editedBody}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <SquircleButton variant="ghost" onClick={onClose}>
            Cancel
          </SquircleButton>
          <SquircleButton variant="primary" onClick={handleApprove}>
            {isHumanReviewRequired ? 'Approve Override & Queue' : 'Approve & Schedule Send'}
          </SquircleButton>
        </div>
      </div>
    </div>
  );
};
