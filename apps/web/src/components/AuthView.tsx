import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Mail,
  Building2,
  Sparkles,
  ArrowRight,
  Zap,
  CheckCircle2,
  AlertCircle,
  Layers,
  Database,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput } from './ui/SquircleInput';
import { ThemePicker } from './ui/ThemePicker';
import { useAuth } from '../context/AuthContext';

export const AuthView: React.FC = () => {
  const { login, register, loginDemo } = useAuth();

  const [mode, setMode] = useState<'LOGIN' | 'SIGNUP'>('LOGIN');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email || !password) {
      setErrorMessage('Please enter your work email and password.');
      return;
    }

    if (mode === 'SIGNUP' && !workspaceName.trim()) {
      setErrorMessage('Please enter an organization / workspace name.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'LOGIN') {
        await login(email, password);
      } else {
        await register(email, password, workspaceName.trim());
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoSignIn = () => {
    setErrorMessage(null);
    loginDemo();
  };

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)] flex flex-col justify-between p-4 sm:p-6 md:p-10 relative overflow-hidden font-sans">
      {/* Dynamic Ambient Background Glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-[var(--accent-glow)] rounded-full blur-3xl pointer-events-none opacity-60" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-[var(--accent-glow)] rounded-full blur-3xl pointer-events-none opacity-50" />

      {/* Top Header Bar */}
      <header className="relative z-10 max-w-7xl w-full mx-auto flex items-center justify-between pb-6">
        {/* Monogram Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[14px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-sm flex items-center justify-center border border-[var(--accent-border)] shadow-xs">
            SDR
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-[var(--text-primary)]">
              Codenter AI SDR
            </h1>
            <p className="text-[11px] text-[var(--text-muted)] font-medium">
              Enterprise Autonomous Sales Platform
            </p>
          </div>
        </div>

        {/* Dynamic Theme Picker */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--text-muted)] hidden sm:inline">Theme:</span>
          <ThemePicker />
        </div>
      </header>

      {/* Main Authentication Centered Hero */}
      <main className="relative z-10 max-w-5xl w-full mx-auto my-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center py-6">
        {/* Left Column: Product Value & Architectural Badges */}
        <div className="lg:col-span-6 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--accent-subtle)] border border-[var(--accent-border)] text-[var(--accent-primary)] text-xs font-bold shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous Outbound &amp; Inbound SDR</span>
          </div>

          <div className="space-y-3">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[var(--text-primary)] leading-tight">
              Scale revenue with{' '}
              <span className="text-[var(--accent-primary)]">100% grounded</span> sales intelligence.
            </h2>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
              Enterprise-grade AI sales development platform. Scrapes verified company facts, personalizes multi-step sequences, enforces deterministic opt-outs, and books meetings automatically.
            </p>
          </div>

          {/* Core Architectural Pillars */}
          <div className="space-y-3 pt-2">
            {[
              {
                icon: ShieldCheck,
                title: 'Deterministic Opt-Out Interception',
                desc: 'Pre-LLM regex gate guarantees 100% unsubscribe recall before token spend.',
              },
              {
                icon: Database,
                title: 'Strict Multi-Tenant Isolation',
                desc: 'Every business query is cryptographically bounded to authenticated workspace claims.',
              },
              {
                icon: Layers,
                title: '14-Intent Taxonomy & Grounded Replies',
                desc: 'Anti-hallucination engine verifies all pricing and SLAs against knowledge chunks.',
              },
            ].map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <div
                  key={idx}
                  className="flex items-start gap-3.5 p-3.5 rounded-[18px] bg-white/60 border border-white/80 shadow-xs"
                >
                  <div className="w-8 h-8 rounded-[12px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[var(--text-primary)]">{feature.title}</h4>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5 leading-normal">
                      {feature.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: 3D Frosted Glass Sign In / Sign Up Card */}
        <div className="lg:col-span-6">
          <FrostedGlassCard className="p-7 sm:p-9 rounded-[32px] shadow-[var(--shadow-glass-elevated)] border border-white/90 space-y-6">
            {/* Mode Switcher Tabs */}
            <div className="flex p-1 bg-slate-100/80 rounded-[16px] border border-slate-200/50">
              <button
                type="button"
                onClick={() => {
                  setMode('LOGIN');
                  setErrorMessage(null);
                }}
                className={`flex-1 py-2 rounded-[12px] text-xs font-bold transition-all duration-200 ${
                  mode === 'LOGIN'
                    ? 'bg-white text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('SIGNUP');
                  setErrorMessage(null);
                }}
                className={`flex-1 py-2 rounded-[12px] text-xs font-bold transition-all duration-200 ${
                  mode === 'SIGNUP'
                    ? 'bg-white text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Create Account
              </button>
            </div>

            <div>
              <h3 className="text-xl font-bold text-[var(--text-primary)]">
                {mode === 'LOGIN' ? 'Welcome Back' : 'Create Workspace'}
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {mode === 'LOGIN'
                  ? 'Sign in to access your autonomous campaigns and live pipeline.'
                  : 'Start your enterprise SDR workspace with full tenant isolation.'}
              </p>
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="p-3.5 rounded-[16px] bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-2.5 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Interactive Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'SIGNUP' && (
                <SquircleInput
                  label="Organization / Workspace Name"
                  type="text"
                  placeholder="e.g. Acme Corp Sales"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  icon={<Building2 className="w-4 h-4" />}
                  required
                />
              )}

              <SquircleInput
                label="Work Email Address"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<Mail className="w-4 h-4" />}
                required
              />

              <SquircleInput
                label="Password"
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock className="w-4 h-4" />}
                required
              />

              <SquircleButton
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                className="w-full py-3 text-sm font-bold shadow-md shadow-[var(--accent-glow)] flex items-center justify-center gap-2 mt-2"
              >
                <span>{mode === 'LOGIN' ? 'Sign In to Workspace' : 'Create Enterprise Account'}</span>
                <ArrowRight className="w-4 h-4" />
              </SquircleButton>
            </form>

            {/* Divider */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200/80" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-white/80 px-3 text-[var(--text-muted)] font-bold tracking-wider rounded-full">
                  Or Instant Demo
                </span>
              </div>
            </div>

            {/* 1-Click Demo Evaluation Button */}
            <SquircleButton
              type="button"
              variant="frosted"
              size="md"
              onClick={handleDemoSignIn}
              className="w-full py-2.5 text-xs font-bold text-slate-800 flex items-center justify-center gap-2 hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)] transition-all"
            >
              <Zap className="w-4 h-4 text-amber-500 fill-amber-500" />
              <span>⚡ 1-Click Demo Enterprise Access</span>
            </SquircleButton>

            {/* Security Guarantee Footer */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-medium">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                AES-256-GCM Encrypted
              </span>
              <span>15-min JWT Session</span>
              <span>Single Tenant Isolation</span>
            </div>
          </FrostedGlassCard>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 max-w-7xl w-full mx-auto pt-6 text-center text-xs text-[var(--text-muted)]">
        Codenter AI SDR Platform © 2026 • Compliant with Section 1.3 Provider Standards &amp; Section 17 Design System
      </footer>
    </div>
  );
};
