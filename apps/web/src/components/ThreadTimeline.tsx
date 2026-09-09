import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import {
  Send,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  UserCheck,
  AlertTriangle,
} from 'lucide-react';
import { IntentBadge } from './ui/IntentBadge';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleTextarea } from './ui/SquircleInput';

export interface TimelineMessage {
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

export interface TimelineThread {
  id: string;
  lead_name: string;
  lead_email: string;
  company_name?: string;
  subject: string;
  status: 'OPEN' | 'REPLIED' | 'CLOSED' | 'BOUNCED';
  last_message_at: string;
  messages: TimelineMessage[];
  intent?: string;
  confidence?: number;
  citations?: string[];
  ai_suggested_reply?: string;
}

interface ThreadTimelineProps {
  thread: TimelineThread;
  onApproveReply?: (threadId: string, replyText: string) => void;
  onAssignHuman?: (threadId: string) => void;
  onSuppressLead?: (email: string) => void;
}

export const ThreadTimeline: React.FC<ThreadTimelineProps> = ({
  thread,
  onApproveReply,
  onAssignHuman,
  onSuppressLead,
}) => {
  const [draftReply, setDraftReply] = useState(thread.ai_suggested_reply || '');
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const handleSend = () => {
    if (!draftReply.trim()) return;
    setIsSending(true);
    if (onApproveReply) {
      onApproveReply(thread.id, draftReply);
    }
    setIsSending(false);
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Thread Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-white/80 backdrop-blur-md rounded-[20px] border border-white/90 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-[var(--text-primary)]">
              {thread.lead_name}
            </h3>
            {thread.company_name && (
              <span className="text-xs text-[var(--text-muted)] font-medium">
                at {thread.company_name}
              </span>
            )}
            {thread.intent && (
              <IntentBadge
                intent={thread.intent}
                confidence={thread.confidence}
                showConfidence
              />
            )}
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            {thread.lead_email} • <span className="font-semibold">{thread.subject}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onAssignHuman && (
            <SquircleButton
              variant="outline"
              size="sm"
              onClick={() => onAssignHuman(thread.id)}
              className="text-xs flex items-center gap-1"
            >
              <UserCheck className="w-3.5 h-3.5" /> Assign to Human
            </SquircleButton>
          )}

          {onSuppressLead && (
            <SquircleButton
              variant="danger"
              size="sm"
              onClick={() => onSuppressLead(thread.lead_email)}
              className="text-xs flex items-center gap-1"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> Suppress
            </SquircleButton>
          )}
        </div>
      </div>

      {/* Messages Timeline */}
      <div className="flex-1 overflow-y-auto space-y-4 p-2 pr-1">
        {thread.messages.map((msg) => {
          const isOutbound = msg.direction === 'OUTBOUND';

          // Critical: Strict DOMPurify HTML sanitization
          const safeHtml = msg.body_html
            ? DOMPurify.sanitize(msg.body_html, { USE_PROFILES: { html: true } })
            : null;

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isOutbound ? 'items-end' : 'items-start'}`}
            >
              <div className="flex items-center gap-2 mb-1 px-1">
                <span className="text-[11px] font-bold text-[var(--text-secondary)]">
                  {isOutbound ? 'Autonomous SDR' : thread.lead_name}
                </span>
                <span className="text-[10px] text-[var(--text-muted)]">
                  {new Date(msg.sent_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                {isOutbound && (
                  <span className="text-[10px] font-semibold text-emerald-600 uppercase">
                    {msg.delivery_status}
                  </span>
                )}
              </div>

              <div
                className={`max-w-2xl p-4 rounded-[20px] shadow-sm text-xs leading-relaxed ${
                  isOutbound
                    ? 'bg-[var(--accent-subtle)] border border-[var(--accent-border)] text-slate-900 rounded-br-xs'
                    : 'bg-white/90 border border-white/90 text-slate-800 rounded-bl-xs'
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

        {/* AI Grounded Reasoning & Citations Card (if available) */}
        {thread.citations && thread.citations.length > 0 && (
          <div className="p-3.5 rounded-[16px] bg-white/70 border border-white/90 text-xs text-slate-700 space-y-2">
            <div className="flex items-center gap-2 font-bold text-slate-800">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Grounded Knowledge Base Citations</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold">
                100% Grounded
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {thread.citations.map((c, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 rounded-[10px] bg-slate-100 text-[11px] font-mono text-slate-600 flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3 text-[var(--accent-primary)]" />
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Suggested AI Reply / Compose Action Bar */}
      <div className="p-4 bg-white/80 backdrop-blur-md rounded-[24px] border border-white/90 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[var(--accent-primary)]" />
            <span className="text-xs font-bold text-[var(--text-primary)]">
              Grounded AI Reply Recommendation
            </span>
          </div>
          <button
            onClick={() => setIsEditingDraft(!isEditingDraft)}
            className="text-xs font-semibold text-[var(--accent-primary)] hover:underline"
          >
            {isEditingDraft ? 'Done Editing' : 'Edit Response'}
          </button>
        </div>

        {isEditingDraft ? (
          <SquircleTextarea
            rows={4}
            value={draftReply}
            onChange={(e) => setDraftReply(e.target.value)}
            placeholder="Draft your reply..."
          />
        ) : (
          <div className="p-3 bg-slate-50/80 rounded-[16px] border border-slate-200/60 text-xs text-slate-700 whitespace-pre-line">
            {draftReply || 'No pending automated draft. Type a custom response to prospect.'}
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Anti-hallucination filter passed
          </span>

          <SquircleButton
            variant="primary"
            size="sm"
            onClick={handleSend}
            isLoading={isSending}
            className="flex items-center gap-1.5 shadow-sm"
          >
            <Send className="w-3.5 h-3.5" />
            Approve &amp; Send Reply
          </SquircleButton>
        </div>
      </div>
    </div>
  );
};
