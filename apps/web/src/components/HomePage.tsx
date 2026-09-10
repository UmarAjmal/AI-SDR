import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Globe,
  Database,
  Calendar,
  Mail,
  Lock,
  Bot,
  Flame,
  BarChart3,
  LogOut,
} from 'lucide-react';
import { SquircleButton } from './ui/SquircleButton';
import { IntentBadge } from './ui/IntentBadge';
import { ThemePicker } from './ui/ThemePicker';
import { useAuth } from '../context/AuthContext';
import { AuthModal } from './AuthModal';

interface HomePageProps {
  onGoToConsole: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onGoToConsole }) => {
  const { isAuthenticated, user, workspace, logout } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('login');

  const openAuth = (mode: 'login' | 'signup') => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  const handleHeroCTA = () => {
    if (isAuthenticated) {
      onGoToConsole();
    } else {
      openAuth('signup');
    }
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] font-sans selection:bg-[var(--accent-subtle)] selection:text-[var(--accent-primary)]">
      {/* 1. Top Apple Frosted Acrylic Sticky Navbar */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-white/80 shadow-[var(--shadow-glass)] px-6 py-4 transition-all">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo & Brand Monogram */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="w-10 h-10 rounded-[14px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-sm flex items-center justify-center border border-[var(--accent-border)] shadow-xs">
              SDR
            </div>
            <div>
              <span className="text-base font-extrabold tracking-tight text-[var(--text-primary)]">
                Codenter <span className="text-[var(--accent-primary)]">AI SDR</span>
              </span>
              <p className="text-[10px] text-[var(--text-muted)] font-medium">
                Autonomous Sales Intelligence
              </p>
            </div>
          </div>

          {/* Navigation Anchors */}
          <nav className="hidden lg:flex items-center gap-6 text-xs font-semibold text-[var(--text-secondary)]">
            <button onClick={() => scrollToSection('golden-path')} className="hover:text-[var(--accent-primary)] transition-colors">
              Golden Path
            </button>
            <button onClick={() => scrollToSection('stop-rules')} className="hover:text-[var(--accent-primary)] transition-colors">
              Safety & 9 Stop Rules
            </button>
            <button onClick={() => scrollToSection('intent-taxonomy')} className="hover:text-[var(--accent-primary)] transition-colors">
              14-Intent Taxonomy
            </button>
            <button onClick={() => scrollToSection('architecture')} className="hover:text-[var(--accent-primary)] transition-colors">
              System Architecture
            </button>
          </nav>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3">
            <ThemePicker />

            {/* If NOT Authenticated: Show Sign In & Sign Up buttons */}
            {!isAuthenticated ? (
              <div className="flex items-center gap-2">
                <SquircleButton
                  variant="frosted"
                  size="sm"
                  onClick={() => openAuth('login')}
                  className="hidden sm:inline-flex text-xs font-bold"
                >
                  Sign In
                </SquircleButton>
                <SquircleButton
                  variant="primary"
                  size="sm"
                  onClick={() => openAuth('signup')}
                  className="text-xs font-bold shadow-sm"
                >
                  Sign Up
                </SquircleButton>
              </div>
            ) : (
              /* If AUTHENTICATED: Show User Avatar + Console Button */
              <div className="flex items-center gap-3">
                {/* User Avatar Chip */}
                <div className="flex items-center gap-2 py-1 px-2.5 rounded-[16px] bg-white/70 border border-white/90 shadow-xs">
                  <div className="w-7 h-7 rounded-[10px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-bold text-xs flex items-center justify-center border border-[var(--accent-border)]">
                    {user?.email?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <div className="hidden sm:block text-left">
                    <p className="text-[11px] font-bold text-[var(--text-primary)] leading-tight truncate max-w-[130px]">
                      {user?.email}
                    </p>
                    <p className="text-[9px] text-[var(--text-muted)] font-medium">
                      {workspace?.name || 'Workspace'}
                    </p>
                  </div>
                </div>

                {/* Primary Console Button */}
                <SquircleButton
                  variant="primary"
                  size="sm"
                  onClick={onGoToConsole}
                  className="text-xs font-bold shadow-md animate-pulse hover:animate-none"
                >
                  Console
                  <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </SquircleButton>

                {/* Logout Button */}
                <button
                  onClick={logout}
                  title="Sign Out"
                  className="p-2 rounded-[12px] text-slate-400 hover:text-red-600 hover:bg-red-50/80 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="relative pt-12 pb-20 px-6 overflow-hidden">
        {/* Ambient Acrylic Gradient Glows */}
        <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[750px] h-[350px] bg-gradient-to-tr from-[var(--accent-glow)] via-blue-100/40 to-indigo-100/30 blur-3xl -z-10 pointer-events-none rounded-full" />

        <div className="max-w-6xl mx-auto text-center space-y-8">
          {/* Spec Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-[16px] bg-white/80 backdrop-blur-xl border border-white/90 shadow-xs text-[11px] font-bold text-[var(--accent-primary)]">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Developer Product Specification v1.0 Aligned</span>
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-primary)]" />
            <span className="text-[var(--text-secondary)] font-medium">September 2026</span>
          </div>

          {/* Main Headline */}
          <div className="space-y-4 max-w-4xl mx-auto">
            <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-[var(--text-primary)] leading-[1.12]">
              Website Intelligence <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent-primary)] to-indigo-600">→ CRM →</span> Autonomous Meetings
            </h1>
            <p className="text-base sm:text-lg text-[var(--text-secondary)] max-w-2xl mx-auto font-normal leading-relaxed">
              Codenter learns your business from your website, creates grounded vector embeddings, calculates explainable 0–100 ICP scores, and autonomously handles multi-step sales outreach and replies without hallucination.
            </p>
          </div>

          {/* Hero CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <SquircleButton
              variant="primary"
              size="lg"
              onClick={handleHeroCTA}
              className="w-full sm:w-auto px-8 py-4 text-sm font-bold shadow-xl shadow-[var(--accent-glow)]"
            >
              {isAuthenticated ? 'Open SDR Console' : 'Get Started with Codenter'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </SquircleButton>

            <SquircleButton
              variant="frosted"
              size="lg"
              onClick={() => scrollToSection('golden-path')}
              className="w-full sm:w-auto px-6 py-4 text-sm font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              Explore Golden Path
            </SquircleButton>
          </div>

          {/* Trust Guarantees */}
          <div className="flex flex-wrap items-center justify-center gap-6 pt-4 text-xs font-semibold text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Pre-LLM Deterministic Opt-Out
            </span>
            <span className="flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-blue-600" />
              AES-256-GCM Token Encryption
            </span>
            <span className="flex items-center gap-1.5">
              <Database className="w-4 h-4 text-indigo-600" />
              Supabase pgvector (PostgreSQL 17)
            </span>
            <span className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-amber-600" />
              Anti-Spam Pacing Jitter (120–300s)
            </span>
          </div>

          {/* 3D Frosted Live SDR Simulation Showcase Card */}
          <div className="pt-8 text-left">
            <div className="relative max-w-4xl mx-auto rounded-[32px] bg-white/75 backdrop-blur-2xl border border-white/90 p-6 sm:p-8 shadow-2xl shadow-slate-900/10 shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.95)]">
              {/* Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-100/80">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-[14px] bg-emerald-50 text-emerald-700 font-black flex items-center justify-center border border-emerald-200 shadow-xs">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[var(--text-primary)]">
                        Autonomous Inbound Conversation Engine
                      </span>
                      <span className="px-2 py-0.5 rounded-[10px] bg-emerald-100/80 text-emerald-800 text-[10px] font-bold">
                        Live Simulation
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] font-medium">
                      Lead: Sarah Jenkins • VP of Marketing at CloudScale Inc
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-[var(--text-muted)] font-medium">ICP Rating:</span>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-[14px] bg-orange-50 border border-orange-200 text-orange-700 text-xs font-black">
                    <Flame className="w-3.5 h-3.5 text-orange-500 fill-orange-500" />
                    <span>88 / 100 (HOT LEAD)</span>
                  </div>
                </div>
              </div>

              {/* Simulation Sequence Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6">
                {/* Left: Inbound Prospect Reply */}
                <div className="space-y-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    1. Inbound Prospect Reply Received
                  </p>
                  <div className="p-4 rounded-[20px] bg-slate-50/90 border border-slate-200/70 text-xs text-[var(--text-secondary)] space-y-2">
                    <p className="font-semibold text-[var(--text-primary)]">
                      "Thanks for reaching out. What is your pricing model for mid-market teams, and can we do a quick 15-min demo call next Tuesday?"
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span>MIME Normalized</span> • <span>Quotes Stripped</span> • <span>Provider ID: msg_89412</span>
                    </div>
                  </div>

                  {/* Deterministic Regex Security Gate */}
                  <div className="p-3 rounded-[16px] bg-emerald-50/90 border border-emerald-200/80 flex items-start gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                    <div className="text-[11px]">
                      <span className="font-bold text-emerald-900">Pre-LLM Deterministic Gate: Passed</span>
                      <p className="text-emerald-700">
                        Zero opt-out phrases detected. Sequence safety verified prior to model invocation.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Right: AI Decision, RAG Retrieval & Autonomous Action */}
                <div className="space-y-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    2. AI Classification & Grounded Autonomous Response
                  </p>

                  <div className="space-y-2.5">
                    {/* Classified Intents */}
                    <div className="flex flex-wrap items-center gap-2">
                      <IntentBadge intent="MEETING_REQUEST" />
                      <IntentBadge intent="PRICING" />
                      <span className="text-[11px] font-semibold text-[var(--text-muted)] ml-auto">
                        Confidence: 96.4%
                      </span>
                    </div>

                    {/* Grounded Citation */}
                    <div className="p-3 rounded-[16px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] text-xs text-[var(--text-secondary)] space-y-1">
                      <div className="flex items-center gap-1.5 font-bold text-[var(--accent-primary)] text-[11px]">
                        <Database className="w-3.5 h-3.5" />
                        Grounded pgvector Citation Verified:
                      </div>
                      <p className="text-[11px] text-[var(--text-primary)] font-medium">
                        "Mid-Market package is $499/mo with 3 mailboxes and 1,500 qualified leads. Source: codenter.com/pricing #chunk-04"
                      </p>
                    </div>

                    {/* Proposed Action */}
                    <div className="p-3 rounded-[16px] bg-white border border-slate-200 shadow-xs flex items-center justify-between text-xs font-semibold">
                      <div className="flex items-center gap-2 text-slate-700">
                        <Calendar className="w-4 h-4 text-[var(--accent-primary)]" />
                        <span>Proposed Tuesday 2:00 PM EST (15m buffer)</span>
                      </div>
                      <span className="px-2 py-0.5 rounded-[10px] bg-blue-100 text-blue-700 text-[10px] font-bold">
                        Auto-Drafted
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. The Golden Path (Section 2.1 of Spec) */}
      <section id="golden-path" className="py-20 px-6 border-t border-slate-200/60 bg-white/40">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent-primary)]">
              Section 2.1 • Architectural Specification
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
              The 5-Stage Golden Path
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              From entering your raw website URL to automated calendar confirmation and CRM synchronization.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              {
                step: '01',
                title: 'Website Intelligence',
                icon: Globe,
                desc: 'Crawls high-value pages, strips navigation boilerplate, and creates pgvector (1536) chunks with source provenance.',
              },
              {
                step: '02',
                title: 'ICP Scoring',
                icon: BarChart3,
                desc: 'Calculates explainable 0–100 scores across Fit (40), Relevance (25), Intent (20), and Negative Deductions (-20).',
              },
              {
                step: '03',
                title: 'Bounded Outreach',
                icon: Mail,
                desc: 'Assembles top 2–3 vector chunks (max 3,000 tokens) to generate structured JSON drafts with anti-spam jitter.',
              },
              {
                step: '04',
                title: '14-Intent Reply Agent',
                icon: Bot,
                desc: 'Deterministic regex intercepts opt-outs; classifies remaining replies into 14 intents with >=85% confidence gates.',
              },
              {
                step: '05',
                title: 'Meeting & CRM Sync',
                icon: Calendar,
                desc: 'Converts slots to prospect timezone, locks slots atomically, records provider event ID, and syncs to HubSpot.',
              },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div
                  key={card.step}
                  className="p-5 rounded-[24px] bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] flex flex-col justify-between space-y-4 hover:shadow-lg hover:-translate-y-1 transition-all duration-200"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-[var(--accent-primary)]">{card.step}</span>
                      <div className="w-8 h-8 rounded-[12px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] flex items-center justify-center border border-[var(--accent-border)]">
                        <Icon className="w-4 h-4" />
                      </div>
                    </div>
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">{card.title}</h3>
                    <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{card.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. Safety & 9 Absolute Stop Conditions (Section 6.4 & 16) */}
      <section id="stop-rules" className="py-20 px-6 border-t border-slate-200/60 bg-[var(--bg-canvas)]">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-600">
              Deterministic Rules &gt; AI Guesswork
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
              9 Absolute Stop Conditions
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Outbound sequences halt instantly and irreversibly upon any of these 9 deterministic triggers. No AI output can override them.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { num: '1', title: 'Explicit Unsubscribe', desc: 'Pre-LLM regex intercepts words like "stop", "remove me" with 100.0% recall.' },
              { num: '2', title: 'Hard Bounce / Suppression', desc: 'Mailbox provider returns 5xx error or suppression status.' },
              { num: '3', title: 'Positive Prospect Reply', desc: 'Inbound reply received stops automated follow-ups immediately.' },
              { num: '4', title: 'Calendar Meeting Booked', desc: 'Verified provider event ID received from Google or Outlook Calendar.' },
              { num: '5', title: 'Manual User Suppression', desc: 'Sales rep clicks 1-click pause or suppress in the SDR Inbox.' },
              { num: '6', title: 'Active CRM Sales Deal', desc: 'HubSpot webhook indicates open deal or opportunity in progress.' },
              { num: '7', title: 'Human Handoff Requested', desc: 'Prospect asks for a human or AI confidence score drops below 85%.' },
              { num: '8', title: 'Max Sequence Steps', desc: 'All configured sequence steps (e.g. 4 steps) reach terminal completion.' },
              { num: '9', title: 'Workspace Compliance Block', desc: 'Daily mailbox sending cap reached or billing threshold exceeded.' },
            ].map((rule) => (
              <div
                key={rule.num}
                className="p-5 rounded-[22px] bg-white/70 backdrop-blur-xl border border-white/80 shadow-xs flex items-start gap-3.5"
              >
                <div className="w-7 h-7 rounded-[10px] bg-rose-50 border border-rose-200 text-rose-700 font-black text-xs flex items-center justify-center shrink-0">
                  {rule.num}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[var(--text-primary)]">{rule.title}</h4>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1 leading-normal">{rule.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. 14-Intent Taxonomy Matrix (Section 8.1) */}
      <section id="intent-taxonomy" className="py-20 px-6 border-t border-slate-200/60 bg-white/40">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent-primary)]">
              Section 8.1 • Inbound Classification
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
              14-Intent Taxonomy Architecture
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Replies are classified with structured schemas before deciding whether AI can respond autonomously or route to the human inbox.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {[
              { intent: 'POSITIVE_INTEREST', desc: 'Prospect is interested; moves toward meeting' },
              { intent: 'PRICING', desc: 'Asks cost; grounded in verified public pricing' },
              { intent: 'PRODUCT_QUESTION', desc: 'Feature query; answers from knowledge chunk' },
              { intent: 'OBJECTION', desc: 'Budget/timing hesitation; handles safely' },
              { intent: 'REQUEST_INFO', desc: 'Requests collateral or PDF summary' },
              { intent: 'NOT_INTERESTED', desc: 'Prospect declined; sequence stopped' },
              { intent: 'UNSUBSCRIBE', desc: 'Opt-out; instant 100% suppression' },
              { intent: 'WRONG_PERSON', desc: 'Not responsible; captures new contact' },
              { intent: 'REFERRAL', desc: 'Points to colleague; updates CRM' },
              { intent: 'TIMING', desc: 'Revisit later; pauses sequence until date' },
              { intent: 'MEETING_REQUEST', desc: 'Wants to meet; triggers calendar slot locking' },
              { intent: 'HUMAN_REQUEST', desc: 'Asks for human; halts AI auto-replies' },
              { intent: 'OUT_OF_SCOPE', desc: 'Ambiguous inquiry; safe handoff created' },
              { intent: 'AUTO_REPLY', desc: 'OOO responder; disregarded from sales funnel' },
            ].map((item) => (
              <div
                key={item.intent}
                className="p-3.5 rounded-[18px] bg-white/75 backdrop-blur-xl border border-white/80 shadow-xs flex flex-col justify-between space-y-2"
              >
                <IntentBadge intent={item.intent} />
                <p className="text-[11px] text-[var(--text-secondary)] leading-tight">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. System Architecture & Tech Stack (Section 3 & 12) */}
      <section id="architecture" className="py-20 px-6 border-t border-slate-200/60 bg-[var(--bg-canvas)]">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              Section 12 • Enterprise Multi-Tenant Infrastructure
            </span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
              Production Architecture & Storage
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Engineered with single-source-of-truth PostgreSQL 17 + pgvector, distributed Redis locks, and 5-question audit telemetry.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-[24px] bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] space-y-3">
              <div className="w-10 h-10 rounded-[14px] bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center font-bold">
                <Database className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">Supabase PostgreSQL 17</h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                24 normalized tables strictly adhering to Section 12, with pgvector (1536) cosine index, uuid-ossp, and multi-tenant workspace isolation.
              </p>
            </div>

            <div className="p-6 rounded-[24px] bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] space-y-3">
              <div className="w-10 h-10 rounded-[14px] bg-indigo-50 border border-indigo-200 text-indigo-700 flex items-center justify-center font-bold">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">AES-256-GCM Encryption</h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                All OAuth tokens and provider secrets encrypted at rest with fresh initialization vectors and authentication tags. 15-min JWT access sessions.
              </p>
            </div>

            <div className="p-6 rounded-[24px] bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] space-y-3">
              <div className="w-10 h-10 rounded-[14px] bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center font-bold">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[var(--text-primary)]">5-Question Audit Trail</h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Every action emits an immutable event recording what happened, rule allowed, model version, source chunks used, and state changed.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Bottom Call-to-Action Banner */}
      <section className="py-20 px-6 border-t border-slate-200/60 bg-white/60">
        <div className="max-w-4xl mx-auto rounded-[32px] bg-gradient-to-tr from-white via-white/90 to-blue-50/50 backdrop-blur-2xl border border-white/90 p-8 sm:p-12 text-center space-y-6 shadow-xl shadow-[var(--accent-glow)]">
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-[var(--text-primary)]">
            Ready to deploy your autonomous SDR?
          </h2>
          <p className="text-sm text-[var(--text-secondary)] max-w-xl mx-auto">
            Train your business model from your website, import CRM leads, and launch your first campaign in under 5 minutes.
          </p>
          <div className="flex justify-center">
            <SquircleButton
              variant="primary"
              size="lg"
              onClick={handleHeroCTA}
              className="px-8 py-4 text-sm font-bold shadow-lg"
            >
              {isAuthenticated ? 'Open SDR Console' : 'Get Started Free'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </SquircleButton>
          </div>
        </div>
      </section>

      {/* 8. Footer */}
      <footer className="py-8 px-6 border-t border-slate-200/80 bg-white/80 text-center text-xs text-[var(--text-muted)] space-y-2">
        <p className="font-bold text-[var(--text-primary)]">Codenter AI SDR Platform • Production Architecture v1.0</p>
        <p>Grounded RAG • Deterministic Compliance • Multi-Tenant Isolated • Apple Frosted Acrylic Design</p>
      </footer>

      {/* Auth Modal for Sign In / Sign Up */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
      />
    </div>
  );
};
