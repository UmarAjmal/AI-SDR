import React, { useState } from 'react';
import { Mail, Lock, User, Building, ArrowRight, Eye, EyeOff, Sparkles, ShieldCheck } from 'lucide-react';
import { SquircleModal } from './ui/SquircleModal';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput } from './ui/SquircleInput';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'signup';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  initialMode = 'login',
}) => {
  const { login, register, loginDemo } = useAuth();
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [companyName, setCompanyName] = useState('');

  // Reset errors when switching mode
  const handleSwitchMode = (newMode: 'login' | 'signup') => {
    setMode(newMode);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      if (mode === 'login') {
        await login(email.trim(), password);
      } else {
        // Genuine signup without asking for workspace
        await register({
          email: email.trim(),
          password,
          firstName: firstName.trim() || undefined,
          lastName: lastName.trim() || undefined,
          companyName: companyName.trim() || undefined,
        });
      }
      // On success, close modal and stay on page (Home page updates with Console button)
      onClose();
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check your details.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = () => {
    loginDemo();
    onClose();
  };

  return (
    <SquircleModal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="md"
    >
      <div className="space-y-6">
        {/* Brand & Title Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-[18px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] font-black text-base border border-[var(--accent-border)] shadow-sm shadow-[var(--accent-glow)] mb-1">
            SDR
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {mode === 'login' ? 'Welcome Back' : 'Create Your Account'}
          </h2>
          <p className="text-xs text-[var(--text-secondary)] max-w-sm mx-auto">
            {mode === 'login'
              ? 'Sign in to access your autonomous SDR workspace, campaigns, and inbox.'
              : 'Join the next-generation autonomous AI sales development platform.'}
          </p>
        </div>

        {/* Segmented Squircle Switcher */}
        <div className="flex bg-slate-100/80 p-1.5 rounded-[18px] border border-slate-200/60 shadow-inner">
          <button
            type="button"
            onClick={() => handleSwitchMode('login')}
            className={`flex-1 py-2 rounded-[14px] text-xs font-bold transition-all duration-200 ${
              mode === 'login'
                ? 'bg-white text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => handleSwitchMode('signup')}
            className={`flex-1 py-2 rounded-[14px] text-xs font-bold transition-all duration-200 ${
              mode === 'signup'
                ? 'bg-white text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3.5 rounded-[16px] bg-red-50/90 border border-red-200/80 text-red-700 text-xs font-medium flex items-center gap-2 animate-in fade-in">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
            {error}
          </div>
        )}

        {/* Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'signup' && (
            <>
              {/* First & Last Name Grid */}
              <div className="grid grid-cols-2 gap-3">
                <SquircleInput
                  label="First Name"
                  placeholder="e.g. Alex"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  leftIcon={<User className="w-4 h-4" />}
                  required
                />
                <SquircleInput
                  label="Last Name"
                  placeholder="e.g. Vance"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>

              {/* Company Name */}
              <SquircleInput
                label="Company Name"
                placeholder="e.g. Acme Software Inc"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                leftIcon={<Building className="w-4 h-4" />}
                hint="Your workspace will be initialized automatically"
              />
            </>
          )}

          {/* Work Email */}
          <SquircleInput
            label="Work Email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="w-4 h-4" />}
            required
          />

          {/* Password with Eye Toggle */}
          <div className="relative">
            <SquircleInput
              label="Password"
              type={showPassword ? 'text' : 'password'}
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="w-4 h-4" />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-slate-400 hover:text-slate-600 focus:outline-none"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
              hint={mode === 'signup' ? 'Minimum 8 characters with numbers & symbols' : undefined}
              required
            />
          </div>

          {/* Submit Button */}
          <SquircleButton
            type="submit"
            variant="primary"
            className="w-full justify-center py-3 text-sm shadow-md"
            isLoading={isLoading}
          >
            {mode === 'login' ? 'Sign In to Account' : 'Create Free Account'}
            {!isLoading && <ArrowRight className="w-4 h-4 ml-2" />}
          </SquircleButton>
        </form>

        {/* Demo Fast Track Button */}
        <div className="pt-2 border-t border-slate-100/90 text-center space-y-3">
          <p className="text-[11px] text-[var(--text-muted)] font-medium">
            Want to test without registering credentials?
          </p>
          <button
            type="button"
            onClick={handleDemoLogin}
            className="w-full py-2.5 px-4 rounded-[16px] bg-slate-50 hover:bg-slate-100/90 border border-slate-200/80 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all flex items-center justify-center gap-2"
          >
            <Sparkles className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
            Continue with Instant Demo Session
          </button>
        </div>

        {/* Security / Compliance Badge */}
        <div className="flex items-center justify-center gap-2 text-[10px] text-[var(--text-muted)] font-medium">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>AES-256-GCM Encrypted • Multi-Tenant Isolated • Spec v1.0</span>
        </div>
      </div>
    </SquircleModal>
  );
};
