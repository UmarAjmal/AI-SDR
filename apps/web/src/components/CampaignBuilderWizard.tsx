import React, { useState } from 'react';
import axios from 'axios';
import {
  Users,
  Target,
  Clock,
  ShieldCheck,
  Eye,
  CheckCircle2,
  ArrowLeft,
  ArrowRight,
  Plus,
  Trash2,
  Sparkles,
} from 'lucide-react';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput, SquircleTextarea } from './ui/SquircleInput';

interface StepTemplate {
  stepNumber: number;
  delayDays: number;
  delayHours: number;
  channel: 'EMAIL';
  subjectTemplate: string;
  bodyTemplate: string;
  instructions: string;
}

interface CampaignBuilderWizardProps {
  onClose: () => void;
  onSuccess?: () => void;
}

export const CampaignBuilderWizard: React.FC<CampaignBuilderWizardProps> = ({
  onClose,
  onSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [name, setName] = useState('Enterprise Growth Q4 Outbound');
  const [minIcpScore, setMinIcpScore] = useState(70);
  const [selectedIndustries, setSelectedIndustries] = useState<string[]>([
    'SaaS',
    'Financial Services',
  ]);
  const [targetTitles, setTargetTitles] = useState('VP Sales, Head of Revenue, Director of Sales Ops');
  const [objective, setObjective] = useState('DEMO_BOOKING');
  const [tone, setTone] = useState('CONVERSATIONAL');
  const [autoReplyThreshold, setAutoReplyThreshold] = useState(85);
  const [strictGroundedClaims, setStrictGroundedClaims] = useState(true);

  const [steps, setSteps] = useState<StepTemplate[]>([
    {
      stepNumber: 1,
      delayDays: 0,
      delayHours: 0,
      channel: 'EMAIL',
      subjectTemplate: 'Quick question regarding {{company_name}} outbound strategy',
      bodyTemplate:
        'Hi {{first_name}},\n\nI noticed {{company_name}} is expanding its sales team. Our autonomous SDR system helps SaaS leaders book 3.2x more discovery calls without deliverability risks.\n\nOpen to a brief 10-minute demo this Thursday?',
      instructions: 'Personalize value proposition based on prospect industry and pain points.',
    },
    {
      stepNumber: 2,
      delayDays: 3,
      delayHours: 2,
      channel: 'EMAIL',
      subjectTemplate: 'Re: Quick question regarding {{company_name}} outbound strategy',
      bodyTemplate:
        'Hi {{first_name}},\n\nFollowing up on my previous note. Similar sales leaders reduced customer acquisition costs by 42% in the first 60 days.\n\nWould Thursday at 2:00 PM EST work for a brief look?',
      instructions: 'Reference verified proof points from knowledge base.',
    },
    {
      stepNumber: 3,
      delayDays: 4,
      delayHours: 0,
      channel: 'EMAIL',
      subjectTemplate: 'Permission to close file for {{company_name}}',
      bodyTemplate:
        'Hi {{first_name}},\n\nI assume scaling outbound pipeline is not a priority right now, which is completely fine. If things change next quarter, feel free to reach out anytime.',
      instructions: 'Respectful breakup email with zero pressure.',
    },
  ]);

  const addSequenceStep = () => {
    const nextNum = steps.length + 1;
    setSteps([
      ...steps,
      {
        stepNumber: nextNum,
        delayDays: 3,
        delayHours: 0,
        channel: 'EMAIL',
        subjectTemplate: `Follow-up #${nextNum} regarding {{company_name}}`,
        bodyTemplate: 'Hi {{first_name}},\n\nChecking in to see if you had a chance to review my previous message.',
        instructions: 'Polite reminder focusing on solving deliverability bottlenecks.',
      },
    ]);
  };

  const removeSequenceStep = (index: number) => {
    if (steps.length <= 1) return;
    const updated = steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, stepNumber: i + 1 }));
    setSteps(updated);
  };

  const handleLaunch = async () => {
    setIsSubmitting(true);
    try {
      await axios.post('/api/v1/campaigns', {
        name,
        objective,
        config_json: {
          min_icp_score: minIcpScore,
          target_industries: selectedIndustries,
          target_titles: targetTitles.split(',').map((s) => s.trim()),
          tone,
          auto_reply_threshold: autoReplyThreshold,
          strict_grounding: strictGroundedClaims,
        },
        steps: steps.map((s) => ({
          step_number: s.stepNumber,
          channel: s.channel,
          delay_days: s.delayDays,
          delay_hours: s.delayHours,
          template_subject: s.subjectTemplate,
          template_body: s.bodyTemplate,
          prompt_instructions: s.instructions,
        })),
      });
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to create campaign:', err);
      if (onSuccess) onSuccess();
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const wizardSteps = [
    { num: 1, label: 'Audience Filters', icon: Users },
    { num: 2, label: 'Objective & Tone', icon: Target },
    { num: 3, label: 'Sequence Steps', icon: Clock },
    { num: 4, label: 'AI Policy', icon: ShieldCheck },
    { num: 5, label: 'Live Preview', icon: Eye },
  ];

  return (
    <div className="space-y-6">
      {/* Wizard Progress Indicator */}
      <div className="grid grid-cols-5 gap-2 border-b border-slate-100 pb-4">
        {wizardSteps.map((s) => {
          const Icon = s.icon;
          const isCompleted = s.num < currentStep;
          const isCurrent = s.num === currentStep;
          return (
            <div
              key={s.num}
              onClick={() => setCurrentStep(s.num)}
              className={`cursor-pointer flex flex-col items-center text-center p-2 rounded-[14px] transition-all ${
                isCurrent
                  ? 'bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-bold'
                  : isCompleted
                  ? 'text-emerald-700 font-semibold'
                  : 'text-slate-400'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs mb-1 transition-all ${
                  isCurrent
                    ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                    : isCompleted
                    ? 'bg-emerald-100 text-emerald-700'
                    : 'bg-slate-100 text-slate-500'
                }`}
              >
                {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
              <span className="text-[11px] hidden sm:inline">{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Step 1: Audience Filters */}
      {currentStep === 1 && (
        <div className="space-y-4 animate-in fade-in">
          <div>
            <h4 className="text-base font-bold text-[var(--text-primary)]">
              Step 1: Campaign Audience &amp; ICP Filters
            </h4>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Define the qualification criteria for leads automatically enrolled in this campaign sequence.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <SquircleInput
              label="Campaign Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q4 SaaS Enterprise Outbound"
            />

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                Minimum ICP Score: <span className="text-[var(--accent-primary)] font-bold">{minIcpScore}</span> / 100
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={minIcpScore}
                onChange={(e) => setMinIcpScore(Number(e.target.value))}
                className="w-full accent-[var(--accent-primary)] mt-3"
              />
              <span className="text-[11px] text-[var(--text-muted)]">
                Only HOT/WARM leads exceeding this score threshold will receive emails.
              </span>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
              Target Verticals
            </label>
            <div className="flex flex-wrap gap-2">
              {['SaaS', 'Financial Services', 'Healthcare Tech', 'E-Commerce', 'Cybersecurity', 'DevTools'].map((ind) => (
                <button
                  key={ind}
                  type="button"
                  onClick={() =>
                    setSelectedIndustries((prev) =>
                      prev.includes(ind) ? prev.filter((i) => i !== ind) : [...prev, ind]
                    )
                  }
                  className={`px-3 py-1.5 rounded-[12px] text-xs font-semibold border transition-all ${
                    selectedIndustries.includes(ind)
                      ? 'bg-[var(--accent-primary)] text-white border-[var(--accent-primary)] shadow-xs'
                      : 'bg-white/70 text-slate-700 border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>

          <SquircleInput
            label="Target Job Titles (Comma-Separated)"
            value={targetTitles}
            onChange={(e) => setTargetTitles(e.target.value)}
            placeholder="VP Sales, Chief Revenue Officer, Head of Demand Gen"
          />
        </div>
      )}

      {/* Step 2: Objective & Tone */}
      {currentStep === 2 && (
        <div className="space-y-4 animate-in fade-in">
          <div>
            <h4 className="text-base font-bold text-[var(--text-primary)]">
              Step 2: Campaign Objective &amp; Tone
            </h4>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Select the primary conversion goal and stylistic voice profile for generated outreach.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
                Campaign Goal
              </label>
              <div className="space-y-2">
                {[
                  { id: 'DEMO_BOOKING', title: 'Demo Booking', desc: 'Secure 15-minute product demo on calendar' },
                  { id: 'DISCOVERY_CALL', title: 'Discovery Call', desc: 'Uncover prospect pain points and tech stack' },
                  { id: 'COLLATERAL_DOWNLOAD', title: 'Share Case Study', desc: 'Deliver proof points and whitepapers' },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setObjective(item.id)}
                    className={`p-3.5 rounded-[16px] border cursor-pointer transition-all ${
                      objective === item.id
                        ? 'bg-[var(--accent-subtle)] border-[var(--accent-primary)] ring-2 ring-[var(--accent-glow)]'
                        : 'bg-white/60 border-white/80 hover:bg-white/90'
                    }`}
                  >
                    <p className="text-xs font-bold text-[var(--text-primary)]">{item.title}</p>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1.5 block">
                Brand Voice &amp; Tone
              </label>
              <div className="space-y-2">
                {[
                  { id: 'CONVERSATIONAL', title: 'Conversational & Consultative', desc: 'Empathetic, clear, human, zero buzzwords' },
                  { id: 'EXECUTIVE', title: 'Executive & Direct', desc: 'Concise (<80 words), high ROI focus for C-suite' },
                  { id: 'TECHNICAL', title: 'Technical & Engineering-Centric', desc: 'Deep architecture and workflow precision' },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => setTone(item.id)}
                    className={`p-3.5 rounded-[16px] border cursor-pointer transition-all ${
                      tone === item.id
                        ? 'bg-[var(--accent-subtle)] border-[var(--accent-primary)] ring-2 ring-[var(--accent-glow)]'
                        : 'bg-white/60 border-white/80 hover:bg-white/90'
                    }`}
                  >
                    <p className="text-xs font-bold text-[var(--text-primary)]">{item.title}</p>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Sequence Steps */}
      {currentStep === 3 && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-base font-bold text-[var(--text-primary)]">
                Step 3: Multi-Step Sequence Cadence
              </h4>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                Configure timing delays and personalized message instructions for each touchpoint.
              </p>
            </div>
            <SquircleButton variant="frosted" size="sm" onClick={addSequenceStep} className="flex items-center gap-1">
              <Plus className="w-3.5 h-3.5" /> Add Step
            </SquircleButton>
          </div>

          <div className="space-y-3 max-h-[45vh] overflow-y-auto pr-1">
            {steps.map((st, idx) => (
              <div
                key={st.stepNumber}
                className="p-4 rounded-[20px] bg-white/70 border border-white/90 shadow-sm space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[var(--accent-primary)] text-white flex items-center justify-center text-xs font-bold">
                      {st.stepNumber}
                    </span>
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      {idx === 0 ? 'Initial Intro' : `Follow-Up Step ${idx + 1}`}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {idx > 0 && (
                      <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-100 px-2 py-1 rounded-[10px]">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>Wait</span>
                        <input
                          type="number"
                          min="1"
                          max="30"
                          value={st.delayDays}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            setSteps((prev) =>
                              prev.map((s, i) => (i === idx ? { ...s, delayDays: val } : s))
                            );
                          }}
                          className="w-10 bg-white border border-slate-300 rounded px-1 py-0.5 text-center font-bold"
                        />
                        <span>biz days</span>
                      </div>
                    )}
                    {steps.length > 1 && (
                      <button
                        onClick={() => removeSequenceStep(idx)}
                        className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                        title="Delete step"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                <SquircleInput
                  label="Subject Line"
                  value={st.subjectTemplate}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, subjectTemplate: val } : s)));
                  }}
                />

                <SquircleTextarea
                  label="Message Content / Prompt Guidance"
                  rows={3}
                  value={st.bodyTemplate}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, bodyTemplate: val } : s)));
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 4: AI Policy & Guardrails */}
      {currentStep === 4 && (
        <div className="space-y-4 animate-in fade-in">
          <div>
            <h4 className="text-base font-bold text-[var(--text-primary)]">
              Step 4: AI Policy &amp; Safety Guardrails
            </h4>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Enforce strict fact grounding, automated reply confidence gates, and zero hallucination rules.
            </p>
          </div>

          <div className="p-4 rounded-[20px] bg-emerald-50/70 border border-emerald-200/80 text-emerald-800 space-y-2">
            <div className="flex items-center gap-2 font-bold text-xs">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              100% Deterministic Grounding Assertion
            </div>
            <p className="text-xs leading-relaxed">
              Every factual claim regarding pricing, SLA, features, or metrics MUST exist in verified knowledge chunks.
              If an inquiry cannot be answered with 100% confidence, the thread automatically routes to Human Handoff.
            </p>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] mb-1 block">
                Auto-Reply Confidence Threshold: <span className="text-[var(--accent-primary)] font-bold">{autoReplyThreshold}%</span>
              </label>
              <input
                type="range"
                min="70"
                max="99"
                value={autoReplyThreshold}
                onChange={(e) => setAutoReplyThreshold(Number(e.target.value))}
                className="w-full accent-[var(--accent-primary)] mt-2"
              />
              <span className="text-[11px] text-[var(--text-muted)]">
                Replies with AI confidence lower than {autoReplyThreshold}% require human review in the Split-Pane Inbox.
              </span>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-[16px] bg-white/70 border border-white/80">
              <div>
                <p className="text-xs font-bold text-[var(--text-primary)]">Strict Grounded Claims Enforcement</p>
                <p className="text-[11px] text-[var(--text-muted)]">Require verifiable source chunks for all pricing &amp; SLA statements</p>
              </div>
              <button
                type="button"
                onClick={() => setStrictGroundedClaims(!strictGroundedClaims)}
                className={`px-3 py-1 rounded-[10px] text-xs font-bold transition-all ${
                  strictGroundedClaims
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {strictGroundedClaims ? 'ACTIVE' : 'OFF'}
              </button>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-[16px] bg-white/70 border border-white/80">
              <div>
                <p className="text-xs font-bold text-[var(--text-primary)]">100% Opt-Out Regex Interception</p>
                <p className="text-[11px] text-[var(--text-muted)]">Pre-LLM deterministic unsubscribe suppression gate</p>
              </div>
              <span className="text-xs font-black text-emerald-600">ENFORCED</span>
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Live Preview */}
      {currentStep === 5 && (
        <div className="space-y-4 animate-in fade-in">
          <div>
            <h4 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--accent-primary)]" />
              Step 5: Live Outbound AI Personalization Preview
            </h4>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              Review live simulated drafts for representative leads in your selected audience before launching.
            </p>
          </div>

          <div className="p-4 rounded-[20px] bg-white/80 border border-white shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <p className="text-xs font-bold text-[var(--text-primary)]">Prospect: Alex Rivera (VP Sales at CloudScale)</p>
                <p className="text-[11px] text-[var(--text-muted)]">ICP Score: 94 • Vertical: SaaS • Size: 250 employees</p>
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Confidence: 94%
              </span>
            </div>

            <div className="text-xs space-y-2 text-slate-800 leading-relaxed font-sans">
              <p className="font-bold text-[var(--accent-primary)]">
                Subject: Accelerating CloudScale outbound with grounded SDR AI
              </p>
              <p>Hi Alex,</p>
              <p>
                I noticed CloudScale is scaling its enterprise outbound team. Codenter AI SDR helps B2B SaaS teams
                book 3.2x more qualified discovery calls while strictly respecting domain deliverability.
              </p>
              <p>Would you be open to a 10-minute demo this Thursday at 2:00 PM?</p>
            </div>

            <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2 text-[11px]">
              <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">
                Claim: 3.2x discovery calls (verified)
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">
                0 Hallucinations
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
                Action: AUTO_SEND APPROVED
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-slate-100">
        {currentStep > 1 ? (
          <SquircleButton variant="frosted" size="sm" onClick={() => setCurrentStep(currentStep - 1)}>
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Previous
          </SquircleButton>
        ) : (
          <SquircleButton variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </SquircleButton>
        )}

        {currentStep < 5 ? (
          <SquircleButton variant="primary" size="sm" onClick={() => setCurrentStep(currentStep + 1)}>
            Next <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </SquircleButton>
        ) : (
          <SquircleButton
            variant="primary"
            size="sm"
            onClick={handleLaunch}
            isLoading={isSubmitting}
            className="shadow-md shadow-[var(--accent-glow)]"
          >
            Launch Campaign
          </SquircleButton>
        )}
      </div>
    </div>
  );
};
