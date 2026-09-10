import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Globe,
  Search,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  Edit3,
  ExternalLink,
  AlertCircle,
  Database,
  Layers,
  ShieldCheck,
  Target,
  DollarSign,
  Award,
  Zap,
  Check,
  Plus,
  Trash2,
  ArrowRight,
  HelpCircle,
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput, SquircleTextarea } from './ui/SquircleInput';
import { SquircleModal } from './ui/SquircleModal';
import { useAuth } from '../context/AuthContext';

export interface BusinessProfileData {
  id: string;
  workspace_id: string;
  company_name: string;
  legal_name?: string | null;
  description?: string | null;
  offerings: string[] | any;
  value_propositions: string[] | any;
  industries: string[] | any;
  icp_hints: Record<string, any>;
  pricing?: Record<string, any> | string | null;
  features: string[] | any;
  faqs: Array<{ question: string; answer: string; source_url?: string }>;
  proof: Array<{ client?: string; metric?: string; summary?: string; quote?: string }>;
  brand_voice: Record<string, any>;
  claims_policy: {
    allowed_claims?: string[];
    forbidden_claims?: string[];
    disclaimers?: string[];
  };
  ctas: string[];
  version: number;
  confidence_score: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface WebsiteScanData {
  id: string;
  workspace_id: string;
  url: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'CRAWLING' | 'EXTRACTING' | 'COMPLETED' | 'FAILED' | 'PARTIAL_FAILURE';
  pages_discovered: number;
  pages_crawled: number;
  pages_failed: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

interface ChunkSearchResult {
  chunk_id: string;
  document_id: string;
  source_url: string;
  title: string | null;
  content: string;
  score: number;
}

const CRAWL_PIPELINE_STEPS = [
  { id: 17, name: 'URL Validation & Domain Normalization', desc: 'Verify DNS, sanitize protocol, strip tracking parameters' },
  { id: 18, name: 'Robots.txt & Crawl Policy', desc: 'Parse robots.txt rules, enforce politeness and delay' },
  { id: 19, name: 'Sitemap.xml & Link Discovery', desc: 'Extract high-priority endpoint tree and route links' },
  { id: 20, name: 'Page Prioritization Engine', desc: 'Prioritize /pricing, /about, /product, /faq, /case-studies' },
  { id: 21, name: 'Playwright Browser Rendering', desc: 'Render JavaScript-heavy DOM with dynamic hydration' },
  { id: 22, name: 'Clean Content & Metadata Extraction', desc: 'Capture headings, body text, timestamps, and source URLs' },
  { id: 24, name: 'Noise & Footer Deduplication', desc: 'Strip boilerplates, cookie banners, navigation repetition' },
  { id: 25, name: 'Page & Topic Classification', desc: 'Categorize into offerings, pricing, solutions, or proof' },
  { id: 26, name: 'Structured Fact Extraction', desc: 'Extract claims, metrics, FAQs, and brand tone with provenance' },
  { id: 27, name: 'Chunking & Embedding Generation', desc: 'pgvector 1536-dim embeddings for cosine retrieval' },
  { id: 28, name: 'Section 4.2 Business Profile Generation', desc: 'Populate company, offerings, ICP hints, claims policy' },
  { id: 29, name: 'Quality & Confidence Gate', desc: 'Grounding validation for 0% hallucination SDR messaging' },
];

export const KnowledgeView: React.FC = () => {
  const { workspace: activeWorkspace } = useAuth();

  const [profile, setProfile] = useState<BusinessProfileData | null>(null);
  const [latestScan, setLatestScan] = useState<WebsiteScanData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Scan state
  const [scanUrl, setScanUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [scanNotice, setScanNotice] = useState<string | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);

  // Edit modal state
  const [isEditing, setIsEditing] = useState(false);
  const [editTab, setEditTab] = useState<'company' | 'icp' | 'knowledge' | 'voice'>('company');
  const [editForm, setEditForm] = useState<Partial<BusinessProfileData>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Temporary list input fields for edit mode
  const [newOffering, setNewOffering] = useState('');
  const [newValueProp, setNewValueProp] = useState('');
  const [newIndustry, setNewIndustry] = useState('');
  const [newFeature, setNewFeature] = useState('');
  const [newCta, setNewCta] = useState('');
  const [newAllowedClaim, setNewAllowedClaim] = useState('');
  const [newForbiddenClaim, setNewForbiddenClaim] = useState('');

  // New FAQ / Case Study inputs
  const [newFaqQ, setNewFaqQ] = useState('');
  const [newFaqA, setNewFaqA] = useState('');
  const [newProofClient, setNewProofClient] = useState('');
  const [newProofMetric, setNewProofMetric] = useState('');
  const [newProofSummary, setNewProofSummary] = useState('');

  // Semantic Vector Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChunkSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Scan interval ref
  const pollIntervalRef = useRef<any>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  // Main fetch function: Checks profile and latest scan
  const loadKnowledgeData = useCallback(async () => {
    setIsLoading(true);
    try {
      // 1. Fetch active Business Profile
      let loadedProfile: BusinessProfileData | null = null;
      try {
        const res = await axios.get('/api/v1/business-profile');
        if (res.data && res.data.id) {
          loadedProfile = res.data;
          setProfile(res.data);
          setEditForm(res.data);
        }
      } catch (profileErr: any) {
        if (profileErr.response?.status !== 404) {
          console.error('Error fetching profile:', profileErr);
        }
        setProfile(null);
      }

      // 2. Fetch latest website scan for this workspace
      let loadedScan: WebsiteScanData | null = null;
      try {
        const scanRes = await axios.get('/api/v1/website-scans/latest');
        if (scanRes.data && scanRes.data.id) {
          loadedScan = scanRes.data;
          setLatestScan(scanRes.data);
          setScanUrl(scanRes.data.url);
          setScanStatus(scanRes.data.status);
        }
      } catch (scanErr: any) {
        console.error('Error fetching latest scan:', scanErr);
      }

      // 3. If a grounded Business Profile already exists, display it immediately
      if (loadedProfile) {
        setIsScanning(false);
      } else if (
        loadedScan &&
        ['PENDING', 'IN_PROGRESS', 'CRAWLING', 'EXTRACTING'].includes(loadedScan.status)
      ) {
        setIsScanning(true);
        setScanStatus(loadedScan.status);
        pollScanStatus(loadedScan.id);
      } else {
        setIsScanning(false);
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace?.id]);

  useEffect(() => {
    loadKnowledgeData();
  }, [loadKnowledgeData]);

  // Poller for crawling pipeline
  const pollScanStatus = useCallback((scanId: string) => {
    stopPolling();
    let tickCount = 0;

    pollIntervalRef.current = setInterval(async () => {
      tickCount++;
      try {
        const res = await axios.get(`/api/v1/website-scans/${scanId}`);
        const currentScan: WebsiteScanData = res.data;
        setLatestScan(currentScan);
        setScanStatus(currentScan.status);

        // Progressively advance through Section 4.1 pipeline steps based on live status
        if (currentScan.status === 'PENDING') {
          setActiveStepIndex((prev) => Math.min(prev + 1, 3));
        } else if (currentScan.status === 'IN_PROGRESS' || currentScan.status === 'CRAWLING') {
          setActiveStepIndex((prev) => Math.max(prev, Math.min(prev + 1, 7)));
        } else if (currentScan.status === 'EXTRACTING') {
          setActiveStepIndex((prev) => Math.max(prev, Math.min(prev + 1, 10)));
        }

        if (currentScan.status === 'COMPLETED' || currentScan.status === 'PARTIAL_FAILURE') {
          stopPolling();
          // Step 11 is [Quality & Confidence Gate]
          setActiveStepIndex(CRAWL_PIPELINE_STEPS.length - 1);

          setTimeout(async () => {
            setIsScanning(false);
            setScanNotice('Website crawled, grounded facts extracted, and pgvector embeddings stored successfully!');
            // Refresh profile data
            try {
              const profRes = await axios.get('/api/v1/business-profile');
              if (profRes.data) {
                setProfile(profRes.data);
                setEditForm(profRes.data);
              }
            } catch (e) {
              console.error('Error fetching new profile:', e);
            }
            setTimeout(() => setScanNotice(null), 8000);
          }, 1000);
        } else if (currentScan.status === 'FAILED') {
          stopPolling();
          setIsScanning(false);
          setScanNotice(`Crawl pipeline interrupted: ${currentScan.error_message || 'Please check URL reachability'}`);
        } else if (tickCount > 45) {
          // Safety timeout (110s): stop polling and check if profile is ready
          stopPolling();
          setIsScanning(false);
          try {
            const profRes = await axios.get('/api/v1/business-profile');
            if (profRes.data) {
              setProfile(profRes.data);
              setEditForm(profRes.data);
            }
          } catch {}
        }
      } catch (err) {
        stopPolling();
        setIsScanning(false);
      }
    }, 2500);
  }, [stopPolling]);

  // Initiate new scan
  const handleStartScan = async (e?: React.FormEvent, overrideUrl?: string) => {
    if (e) e.preventDefault();
    const target = overrideUrl || scanUrl;
    if (!target.trim()) return;

    let formattedUrl = target.trim();
    if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
      formattedUrl = 'https://' + formattedUrl;
    }

    setIsScanning(true);
    setScanStatus('PENDING');
    setActiveStepIndex(0);
    setScanNotice(`Initializing 4.1 Crawl Pipeline for ${formattedUrl}...`);

    try {
      const res = await axios.post('/api/v1/website-scans', { url: formattedUrl });
      const scanId = res.data?.id;
      setLatestScan(res.data);
      pollScanStatus(scanId);
    } catch (err: any) {
      console.error('Failed to start website scan:', err);
      setIsScanning(false);
      const msg = err.response?.data?.detail || 'Failed to dispatch crawler.';
      setScanNotice(`Error: ${msg}`);
      setTimeout(() => setScanNotice(null), 6000);
    }
  };

  // Save changes to Section 4.2 Business Profile
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await axios.put('/api/v1/business-profile', editForm);
      setProfile(res.data);
      setEditForm(res.data);
      setIsEditing(false);
      setScanNotice('Business Profile customizations updated and saved to PostgreSQL successfully.');
      setTimeout(() => setScanNotice(null), 5000);
    } catch (err: any) {
      console.error('Failed to save profile changes:', err);
      alert(err.response?.data?.detail || 'Failed to save changes.');
    } finally {
      setIsSaving(false);
    }
  };

  // Helper helpers to add/remove array items in editForm
  const addArrayItem = (key: keyof BusinessProfileData, value: string, resetFn: (v: string) => void) => {
    if (!value.trim()) return;
    const currentList = Array.isArray(editForm[key]) ? [...(editForm[key] as any[])] : [];
    currentList.push(value.trim());
    setEditForm({ ...editForm, [key]: currentList });
    resetFn('');
  };

  const removeArrayItem = (key: keyof BusinessProfileData, index: number) => {
    const currentList = Array.isArray(editForm[key]) ? [...(editForm[key] as any[])] : [];
    currentList.splice(index, 1);
    setEditForm({ ...editForm, [key]: currentList });
  };

  // Semantic Vector Search Query
  const handleSearchChunks = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);
    try {
      const res = await axios.post('/api/v1/knowledge/search', {
        query: searchQuery.trim(),
        top_k: 3,
      });
      setSearchResults(res.data || []);
    } catch (err: any) {
      console.error('Vector search error:', err);
      setSearchError(err.response?.data?.detail || 'Semantic retrieval failed.');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Normalize array/list data for display
  const toList = (val: any): string[] => {
    if (!val) return [];
    if (Array.isArray(val)) {
      return val.map((item) => (typeof item === 'string' ? item : JSON.stringify(item)));
    }
    if (typeof val === 'object') {
      return Object.entries(val).map(([k, v]) => `${k}: ${v}`);
    }
    return [String(val)];
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Website Intelligence &amp; Knowledge Base
          </h2>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            Authoritative starting point for business grounding, pgvector embeddings, and zero-hallucination SDR messaging.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {latestScan?.url && !isScanning && (
            <SquircleButton
              variant="outline"
              size="sm"
              onClick={() => handleStartScan(undefined, latestScan.url)}
              className="flex items-center gap-1.5 shadow-xs text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-crawl Site
            </SquircleButton>
          )}

          {profile && (
            <SquircleButton
              variant="primary"
              size="sm"
              onClick={() => {
                setEditForm(profile);
                setIsEditing(true);
              }}
              className="flex items-center gap-1.5 shadow-sm text-xs font-bold"
            >
              <Edit3 className="w-3.5 h-3.5" />
              Customize Grounded Data
            </SquircleButton>
          )}
        </div>
      </div>

      {/* Notice Banner */}
      {scanNotice && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/70 text-xs text-blue-900 flex items-center justify-between shadow-xs">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse shrink-0" />
            <span className="font-medium">{scanNotice}</span>
            {scanStatus && (
              <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-blue-200/80 text-blue-900 font-bold uppercase tracking-wide">
                {scanStatus}
              </span>
            )}
          </span>
          <button onClick={() => setScanNotice(null)} className="text-blue-500 hover:text-blue-700 font-bold ml-2">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* State 1: Active Crawling Pipeline In Progress */}
      {isScanning && (
        <FrostedGlassCard elevated className="p-6 md:p-8 space-y-6 border-[var(--accent-border)]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/80">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <RefreshCw className="w-5 h-5 text-[var(--accent-primary)] animate-spin" />
                <h3 className="text-base font-bold text-[var(--text-primary)]">
                  Section 4.1 Crawl Pipeline in Execution
                </h3>
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono">
                Target: {latestScan?.url || scanUrl}
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
              <div className="px-3 py-1 rounded-[12px] bg-white/80 border border-slate-200/80">
                Discovered: <span className="font-bold text-[var(--accent-primary)]">{latestScan?.pages_discovered ?? 0}</span>
              </div>
              <div className="px-3 py-1 rounded-[12px] bg-white/80 border border-slate-200/80">
                Crawled: <span className="font-bold text-emerald-600">{latestScan?.pages_crawled ?? 0}</span>
              </div>
            </div>
          </div>

          {/* Stepper Display */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
            {CRAWL_PIPELINE_STEPS.map((step, idx) => {
              const isPast = idx < activeStepIndex;
              const isCurrent = idx === activeStepIndex;
              return (
                <div
                  key={step.id}
                  className={`p-3 rounded-[16px] border transition-all text-xs flex items-start gap-2.5 ${
                    isPast
                      ? 'bg-emerald-50/70 border-emerald-200/80 text-emerald-900'
                      : isCurrent
                      ? 'bg-[var(--accent-subtle)] border-[var(--accent-border)] text-[var(--accent-primary)] ring-2 ring-[var(--accent-glow)]'
                      : 'bg-white/40 border-slate-200/60 text-slate-400'
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {isPast ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : isCurrent ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-[var(--accent-primary)]" />
                    ) : (
                      <span className="w-4 h-4 rounded-full border border-slate-300 text-[10px] flex items-center justify-center font-bold">
                        {step.id}
                      </span>
                    )}
                  </div>
                  <div className="space-y-0.5">
                    <div className="font-bold text-[11px] leading-tight">{step.name}</div>
                    <div className="text-[10px] opacity-80 leading-snug">{step.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </FrostedGlassCard>
      )}

      {/* State 2: Loading initial state */}
      {isLoading ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Loading Grounded Knowledge Base...</div>
          <div className="text-xs text-[var(--text-muted)]">Verifying source provenance and pgvector document embeddings</div>
        </FrostedGlassCard>
      ) : !profile && !isScanning ? (
        /* State 3: Empty State / Input URL */
        <FrostedGlassCard elevated className="p-10 md:p-16 flex flex-col items-center justify-center text-center space-y-6">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Globe className="w-8 h-8" />
          </div>

          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              No Grounded Business Profile Extracted Yet
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Enter your corporate website URL. Our Section 4 crawl pipeline will index your offerings, pricing, value propositions, and FAQs into vector embeddings for 0% hallucination SDR outreach.
            </p>
          </div>

          <form onSubmit={handleStartScan} className="w-full max-w-lg flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <SquircleInput
                value={scanUrl}
                onChange={(e) => setScanUrl(e.target.value)}
                placeholder="https://yourcompany.com"
                required
              />
            </div>
            <SquircleButton
              variant="primary"
              size="md"
              type="submit"
              isLoading={isScanning}
              className="flex items-center justify-center gap-2 shadow-sm shrink-0"
            >
              <Globe className="w-4 h-4" />
              Launch Crawl Pipeline
            </SquircleButton>
          </form>
        </FrostedGlassCard>
      ) : profile ? (
        /* State 4: Full Section 4.2 Business Profile Dashboard */
        <div className="space-y-6">
          {/* Top Card: Company & Core Identity */}
          <FrostedGlassCard elevated className="p-6 md:p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-6 border-b border-white/80">
              <div className="space-y-1.5 max-w-3xl">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-2xl font-black text-[var(--text-primary)] tracking-tight">
                    {profile.company_name}
                  </h3>
                  {profile.legal_name && (
                    <span className="text-xs text-[var(--text-muted)] font-medium">
                      ({profile.legal_name})
                    </span>
                  )}
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Grounded &amp; Active (v{profile.version})
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Confidence: {Math.round((profile.confidence_score || 1.0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed pt-1">
                  {profile.description || 'No corporate description extracted.'}
                </p>
              </div>

              {/* Pricing badge */}
              {profile.pricing && (
                <div className="p-3.5 rounded-[18px] bg-slate-50/90 border border-slate-200/80 shrink-0 max-w-xs">
                  <div className="flex items-center gap-1.5 text-[10px] uppercase font-bold text-slate-400 mb-1">
                    <DollarSign className="w-3 h-3 text-emerald-600" />
                    Grounded Pricing Model
                  </div>
                  <div className="text-xs font-bold text-slate-800 font-mono break-words">
                    {typeof profile.pricing === 'string'
                      ? profile.pricing
                      : JSON.stringify(profile.pricing)}
                  </div>
                </div>
              )}
            </div>

            {/* Grid 1: Offerings & Value Propositions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Offerings */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                  Extracted Offerings &amp; Services
                </h4>
                <div className="space-y-1.5">
                  {toList(profile.offerings).length > 0 ? (
                    toList(profile.offerings).map((offering, idx) => (
                      <div key={idx} className="text-xs text-slate-700 flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{offering}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 italic">No offerings extracted.</div>
                  )}
                </div>
              </div>

              {/* Value Propositions */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  Core Value Propositions
                </h4>
                <div className="space-y-1.5">
                  {toList(profile.value_propositions).length > 0 ? (
                    toList(profile.value_propositions).map((vp, idx) => (
                      <div key={idx} className="text-xs text-slate-700 flex items-start gap-2">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{vp}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 italic">No value propositions recorded.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Grid 2: Target Industries, ICP Hints & CTAs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
              {/* Target Industries */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-2.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                  Target Industries
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {toList(profile.industries).length > 0 ? (
                    toList(profile.industries).map((ind, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] text-xs font-semibold bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)]"
                      >
                        {ind}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">None defined</span>
                  )}
                </div>
              </div>

              {/* ICP Hints */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-2.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5 text-indigo-600" />
                  ICP Qualification Hints
                </h4>
                <div className="space-y-1 text-xs text-slate-700">
                  {Object.keys(profile.icp_hints || {}).length > 0 ? (
                    Object.entries(profile.icp_hints).map(([k, v], idx) => (
                      <div key={idx} className="flex items-start justify-between gap-2">
                        <span className="font-semibold text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span>
                        <span className="font-medium text-slate-800 text-right">{String(v)}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">No ICP parameters set</span>
                  )}
                </div>
              </div>

              {/* CTAs */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-2.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  Approved CTAs
                </h4>
                <div className="space-y-1.5">
                  {toList(profile.ctas).length > 0 ? (
                    toList(profile.ctas).map((cta, i) => (
                      <div key={i} className="text-xs font-medium text-slate-700 flex items-center gap-2">
                        <ArrowRight className="w-3 h-3 text-amber-500" />
                        <span>{cta}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">Schedule demo, Free trial</span>
                  )}
                </div>
              </div>
            </div>

            {/* Grid 3: FAQs & Proof/Case Studies */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              {/* FAQs */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-2">
                  <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                  Grounded FAQs ({profile.faqs?.length || 0})
                </h4>
                <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                  {profile.faqs && profile.faqs.length > 0 ? (
                    profile.faqs.map((faq, i) => (
                      <div key={i} className="p-2.5 rounded-[12px] bg-white/80 border border-slate-100 space-y-1">
                        <div className="text-xs font-bold text-slate-800">Q: {faq.question}</div>
                        <div className="text-xs text-slate-600">A: {faq.answer}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 italic">No FAQs recorded.</div>
                  )}
                </div>
              </div>

              {/* Proof / Case Studies */}
              <div className="p-4 rounded-[20px] bg-white/70 border border-white/80 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-2">
                  <Award className="w-3.5 h-3.5 text-amber-600" />
                  Proof &amp; Case Studies ({profile.proof?.length || 0})
                </h4>
                <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                  {profile.proof && profile.proof.length > 0 ? (
                    profile.proof.map((item, i) => (
                      <div key={i} className="p-2.5 rounded-[12px] bg-white/80 border border-slate-100 space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-800">{item.client || 'Client Study'}</span>
                          {item.metric && (
                            <span className="px-2 py-0.5 rounded-[6px] bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                              {item.metric}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-600">{item.summary || item.quote}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400 italic">No case studies or testimonials recorded.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Claims Policy & Brand Voice */}
            <div className="p-4 rounded-[20px] bg-slate-50/80 border border-slate-200/80 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Claims Policy &amp; Safety Controls
                </h4>
                <span className="text-[11px] font-semibold text-slate-500">
                  Brand Tone:{' '}
                  <span className="font-bold text-slate-800">
                    {profile.brand_voice?.tone || 'Professional & Direct'}
                  </span>
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="font-semibold text-emerald-700 block mb-1">✓ Allowed Claims:</span>
                  <div className="space-y-1 text-slate-600">
                    {profile.claims_policy?.allowed_claims && profile.claims_policy.allowed_claims.length > 0 ? (
                      profile.claims_policy.allowed_claims.map((claim, i) => (
                        <div key={i}>• {claim}</div>
                      ))
                    ) : (
                      <div className="italic text-slate-400">All verified website facts are allowed.</div>
                    )}
                  </div>
                </div>

                <div>
                  <span className="font-semibold text-red-700 block mb-1">✕ Forbidden Claims (Deterministic Guardrails):</span>
                  <div className="space-y-1 text-slate-600">
                    {profile.claims_policy?.forbidden_claims && profile.claims_policy.forbidden_claims.length > 0 ? (
                      profile.claims_policy.forbidden_claims.map((claim, i) => (
                        <div key={i}>• {claim}</div>
                      ))
                    ) : (
                      <div className="italic text-slate-400">Never fabricate ungrounded discounts, SLAs, or capabilities.</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </FrostedGlassCard>

          {/* RAG Vector Query Tester Card */}
          <FrostedGlassCard className="p-6 md:p-8 space-y-4">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Search className="w-4 h-4 text-[var(--accent-primary)]" />
                Live Semantic Context Retrieval (pgvector)
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                Test how the AI SDR queries cosine similarity against your grounded knowledge base during prospect conversations.
              </p>
            </div>

            <form onSubmit={handleSearchChunks} className="flex gap-3">
              <div className="flex-1">
                <SquircleInput
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g. What is your refund policy? Or what are your SLA terms?"
                />
              </div>
              <SquircleButton
                variant="primary"
                type="submit"
                isLoading={isSearching}
                className="shrink-0 text-xs font-bold"
              >
                Query pgvector
              </SquircleButton>
            </form>

            {searchError && (
              <div className="p-3 rounded-[12px] bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{searchError}</span>
              </div>
            )}

            {searchResults.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Retrieved Knowledge Chunks (Top {searchResults.length})
                </h4>
                <div className="space-y-2.5">
                  {searchResults.map((chk, i) => (
                    <div
                      key={chk.chunk_id || i}
                      className="p-4 rounded-[16px] bg-white/80 border border-white/90 shadow-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-800 truncate">{chk.title || 'Document'}</span>
                        <span className="px-2 py-0.5 rounded-[8px] bg-emerald-50 text-emerald-700 font-mono text-[10px] font-bold">
                          Similarity: {Math.round(chk.score * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">{chk.content}</p>
                      {chk.source_url && (
                        <div className="pt-1 flex items-center gap-1 text-[11px] text-blue-600 hover:underline">
                          <ExternalLink className="w-3 h-3" />
                          <a href={chk.source_url} target="_blank" rel="noopener noreferrer">
                            {chk.source_url}
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </FrostedGlassCard>
        </div>
      ) : null}

      {/* Full Customization Modal (Section 4.2 Schema) */}
      <SquircleModal
        isOpen={isEditing}
        onClose={() => setIsEditing(false)}
        title="Customize Grounded Business Profile"
        maxWidth="2xl"
      >
        <div className="space-y-5 pt-1">
          {/* Tabs */}
          <div className="flex border-b border-slate-200 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setEditTab('company')}
              className={`pb-2.5 px-3 transition-colors border-b-2 ${
                editTab === 'company'
                  ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Company &amp; Offerings
            </button>
            <button
              type="button"
              onClick={() => setEditTab('icp')}
              className={`pb-2.5 px-3 transition-colors border-b-2 ${
                editTab === 'icp'
                  ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              ICP &amp; Strategy
            </button>
            <button
              type="button"
              onClick={() => setEditTab('knowledge')}
              className={`pb-2.5 px-3 transition-colors border-b-2 ${
                editTab === 'knowledge'
                  ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              FAQs &amp; Proof
            </button>
            <button
              type="button"
              onClick={() => setEditTab('voice')}
              className={`pb-2.5 px-3 transition-colors border-b-2 ${
                editTab === 'voice'
                  ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              Voice &amp; Claims Policy
            </button>
          </div>

          <form onSubmit={handleSaveProfile} className="space-y-4">
            {/* Tab 1: Company & Offerings */}
            {editTab === 'company' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <SquircleInput
                    label="Company Name"
                    value={editForm.company_name || ''}
                    onChange={(e) => setEditForm({ ...editForm, company_name: e.target.value })}
                    required
                  />
                  <SquircleInput
                    label="Legal / Business Name"
                    value={editForm.legal_name || ''}
                    onChange={(e) => setEditForm({ ...editForm, legal_name: e.target.value })}
                    placeholder="e.g. Acme Corporation LLC"
                  />
                </div>

                <SquircleTextarea
                  label="Corporate Description"
                  rows={3}
                  value={editForm.description || ''}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                />

                {/* Offerings list editor */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Offerings &amp; Services</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newOffering}
                      onChange={(e) => setNewOffering(e.target.value)}
                      placeholder="Add an offering or product line..."
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => addArrayItem('offerings', newOffering, setNewOffering)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {toList(editForm.offerings).map((item, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] bg-slate-100 text-slate-800 text-xs flex items-center gap-1.5"
                      >
                        <span>{item}</span>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('offerings', i)}
                          className="text-slate-400 hover:text-red-500 font-bold"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Features list editor */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Core Features &amp; Capabilities</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newFeature}
                      onChange={(e) => setNewFeature(e.target.value)}
                      placeholder="Add a product feature..."
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => addArrayItem('features', newFeature, setNewFeature)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {toList(editForm.features).map((item, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] bg-slate-100 text-slate-800 text-xs flex items-center gap-1.5"
                      >
                        <span>{item}</span>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('features', i)}
                          className="text-slate-400 hover:text-red-500 font-bold"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: ICP & Strategy */}
            {editTab === 'icp' && (
              <div className="space-y-4">
                {/* Value Propositions */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Value Propositions</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newValueProp}
                      onChange={(e) => setNewValueProp(e.target.value)}
                      placeholder="e.g. Reduces sales prospecting time by 85%"
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => addArrayItem('value_propositions', newValueProp, setNewValueProp)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                  <div className="space-y-1 pt-1">
                    {toList(editForm.value_propositions).map((item, i) => (
                      <div key={i} className="text-xs text-slate-700 flex items-center justify-between p-2 rounded bg-slate-50">
                        <span>• {item}</span>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('value_propositions', i)}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Industries */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Target Industries</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newIndustry}
                      onChange={(e) => setNewIndustry(e.target.value)}
                      placeholder="e.g. B2B SaaS, FinTech, Healthcare"
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => addArrayItem('industries', newIndustry, setNewIndustry)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {toList(editForm.industries).map((item, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] bg-[var(--accent-subtle)] text-[var(--accent-primary)] text-xs flex items-center gap-1.5"
                      >
                        <span>{item}</span>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('industries', i)}
                          className="text-slate-400 hover:text-red-500 font-bold"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Pricing notes */}
                <SquircleInput
                  label="Pricing Structure"
                  value={
                    typeof editForm.pricing === 'string'
                      ? editForm.pricing
                      : JSON.stringify(editForm.pricing || '')
                  }
                  onChange={(e) => setEditForm({ ...editForm, pricing: e.target.value })}
                  placeholder="e.g. Free Tier, Pro: $49/mo, Enterprise: Custom SLA"
                />
              </div>
            )}

            {/* Tab 3: FAQs & Proof */}
            {editTab === 'knowledge' && (
              <div className="space-y-4">
                {/* FAQs */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Add Grounded FAQ</label>
                  <div className="space-y-2 p-3 rounded-[16px] bg-slate-50 border border-slate-200">
                    <SquircleInput
                      value={newFaqQ}
                      onChange={(e) => setNewFaqQ(e.target.value)}
                      placeholder="Question..."
                    />
                    <SquircleTextarea
                      rows={2}
                      value={newFaqA}
                      onChange={(e) => setNewFaqA(e.target.value)}
                      placeholder="Answer..."
                    />
                    <SquircleButton
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (!newFaqQ.trim() || !newFaqA.trim()) return;
                        const faqs = [...(editForm.faqs || [])];
                        faqs.push({ question: newFaqQ.trim(), answer: newFaqA.trim() });
                        setEditForm({ ...editForm, faqs });
                        setNewFaqQ('');
                        setNewFaqA('');
                      }}
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" /> Add FAQ
                    </SquircleButton>
                  </div>

                  <div className="space-y-1.5 max-h-40 overflow-y-auto">
                    {(editForm.faqs || []).map((faq, i) => (
                      <div key={i} className="p-2 text-xs rounded bg-white border border-slate-200 flex items-start justify-between gap-2">
                        <div>
                          <div className="font-bold text-slate-800">Q: {faq.question}</div>
                          <div className="text-slate-600">A: {faq.answer}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const faqs = [...(editForm.faqs || [])];
                            faqs.splice(i, 1);
                            setEditForm({ ...editForm, faqs });
                          }}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Approved CTAs */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-700 block">Approved CTAs</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newCta}
                      onChange={(e) => setNewCta(e.target.value)}
                      placeholder="e.g. Schedule a 15-min discovery call"
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => addArrayItem('ctas', newCta, setNewCta)}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {toList(editForm.ctas).map((item, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] bg-amber-50 text-amber-800 text-xs flex items-center gap-1.5 border border-amber-200"
                      >
                        <span>{item}</span>
                        <button
                          type="button"
                          onClick={() => removeArrayItem('ctas', i)}
                          className="text-slate-400 hover:text-red-500 font-bold"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Proof / Case Studies editor */}
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <label className="text-xs font-bold text-slate-700 block">Add Case Study / Proof Point</label>
                  <div className="space-y-2 p-3 rounded-[16px] bg-slate-50 border border-slate-200">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <SquircleInput
                        value={newProofClient}
                        onChange={(e) => setNewProofClient(e.target.value)}
                        placeholder="Client / Company name..."
                      />
                      <SquircleInput
                        value={newProofMetric}
                        onChange={(e) => setNewProofMetric(e.target.value)}
                        placeholder="Key metric (e.g. +340% pipeline)..."
                      />
                    </div>
                    <SquircleTextarea
                      rows={2}
                      value={newProofSummary}
                      onChange={(e) => setNewProofSummary(e.target.value)}
                      placeholder="Summary or quote..."
                    />
                    <SquircleButton
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (!newProofClient.trim() && !newProofSummary.trim()) return;
                        const proof = [...(editForm.proof || [])];
                        proof.push({
                          client: newProofClient.trim(),
                          metric: newProofMetric.trim(),
                          summary: newProofSummary.trim(),
                        });
                        setEditForm({ ...editForm, proof });
                        setNewProofClient('');
                        setNewProofMetric('');
                        setNewProofSummary('');
                      }}
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" /> Add Case Study
                    </SquircleButton>
                  </div>

                  <div className="space-y-1.5 max-h-40 overflow-y-auto pt-1">
                    {(editForm.proof || []).map((p, i) => (
                      <div key={i} className="p-2 text-xs rounded bg-white border border-slate-200 flex items-start justify-between gap-2">
                        <div>
                          <div className="font-bold text-slate-800">
                            {p.client} {p.metric && <span className="text-emerald-600 font-mono">({p.metric})</span>}
                          </div>
                          <div className="text-slate-600">{p.summary || p.quote}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const proof = [...(editForm.proof || [])];
                            proof.splice(i, 1);
                            setEditForm({ ...editForm, proof });
                          }}
                          className="text-slate-400 hover:text-red-500"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Voice & Claims Policy */}
            {editTab === 'voice' && (
              <div className="space-y-4">
                <SquircleInput
                  label="Brand Voice & Tone"
                  value={editForm.brand_voice?.tone || 'Professional & Direct'}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      brand_voice: { ...editForm.brand_voice, tone: e.target.value },
                    })
                  }
                  placeholder="e.g. Professional, Authoritative, Helpful, Technical"
                />

                {/* Allowed claims */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-emerald-700 block">Allowed Claims</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newAllowedClaim}
                      onChange={(e) => setNewAllowedClaim(e.target.value)}
                      placeholder="Add an allowed statement..."
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => {
                        if (!newAllowedClaim.trim()) return;
                        const claims = { ...(editForm.claims_policy || {}) };
                        const allowed = [...(claims.allowed_claims || [])];
                        allowed.push(newAllowedClaim.trim());
                        claims.allowed_claims = allowed;
                        setEditForm({ ...editForm, claims_policy: claims });
                        setNewAllowedClaim('');
                      }}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                </div>

                {/* Forbidden claims */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-red-700 block">Forbidden Claims (Deterministic Guardrail)</label>
                  <div className="flex gap-2">
                    <SquircleInput
                      value={newForbiddenClaim}
                      onChange={(e) => setNewForbiddenClaim(e.target.value)}
                      placeholder="Add forbidden claim (e.g. no 50% discount offers)..."
                    />
                    <SquircleButton
                      type="button"
                      variant="outline"
                      onClick={() => {
                        if (!newForbiddenClaim.trim()) return;
                        const claims = { ...(editForm.claims_policy || {}) };
                        const forbidden = [...(claims.forbidden_claims || [])];
                        forbidden.push(newForbiddenClaim.trim());
                        claims.forbidden_claims = forbidden;
                        setEditForm({ ...editForm, claims_policy: claims });
                        setNewForbiddenClaim('');
                      }}
                      className="shrink-0"
                    >
                      <Plus className="w-4 h-4" />
                    </SquircleButton>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-200">
              <SquircleButton
                type="button"
                variant="outline"
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </SquircleButton>
              <SquircleButton
                type="submit"
                variant="primary"
                isLoading={isSaving}
                className="font-bold text-xs shadow-md"
              >
                Save All Customizations
              </SquircleButton>
            </div>
          </form>
        </div>
      </SquircleModal>
    </div>
  );
};
