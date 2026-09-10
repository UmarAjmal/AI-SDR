import React, { useState, useEffect, useCallback } from 'react';
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
} from 'lucide-react';
import { FrostedGlassCard } from './ui/FrostedGlassCard';
import { SquircleButton } from './ui/SquircleButton';
import { SquircleInput, SquircleTextarea } from './ui/SquircleInput';
import { SquircleModal } from './ui/SquircleModal';

interface BusinessProfileData {
  id: string;
  company_name: string;
  description: string;
  value_propositions: string[];
  pricing_model: string;
  target_industries: string[];
  target_roles: string[];
  competitors: string[];
  faqs: { question: string; answer: string }[];
  case_studies: { client: string; metric: string; summary: string }[];
  version: number;
}

interface ChunkSearchResult {
  chunk_id: string;
  document_id: string;
  source_url: string;
  document_title: string;
  content: string;
  similarity_score: number;
}

export const KnowledgeView: React.FC = () => {
  const [profile, setProfile] = useState<BusinessProfileData | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);

  // Scan State
  const [scanUrl, setScanUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [scanNotice, setScanNotice] = useState<string | null>(null);

  // Edit Profile State
  const [isEditing, setIsEditing] = useState(false);
  const [editCompanyName, setEditCompanyName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editPricing, setEditPricing] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Semantic Vector Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChunkSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Fetch Business Profile
  const fetchProfile = useCallback(async () => {
    setIsLoadingProfile(true);
    try {
      const res = await axios.get('/api/v1/business-profile');
      if (res.data) {
        setProfile(res.data);
        setEditCompanyName(res.data.company_name || '');
        setEditDescription(res.data.description || '');
        setEditPricing(res.data.pricing_model || '');
      }
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error('Failed to load profile:', err);
      }
      setProfile(null);
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // Initiate Playwright Website Crawl
  const handleStartScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scanUrl.trim()) return;

    let formattedUrl = scanUrl.trim();
    if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
      formattedUrl = 'https://' + formattedUrl;
    }

    setIsScanning(true);
    setScanStatus('CRAWLING');
    setScanNotice(`Dispatching Playwright headless crawler for ${formattedUrl}...`);

    try {
      const res = await axios.post('/api/v1/website-scans', { url: formattedUrl });
      const scanId = res.data?.id;

      // Poll scan status
      const interval = setInterval(async () => {
        try {
          const checkRes = await axios.get(`/api/v1/website-scans/${scanId}`);
          const currentStatus = checkRes.data?.status;

          if (currentStatus === 'COMPLETED') {
            clearInterval(interval);
            setIsScanning(false);
            setScanStatus('COMPLETED');
            setScanNotice('Website crawled and structured knowledge base extracted successfully!');
            await fetchProfile();
            setTimeout(() => setScanNotice(null), 5000);
          } else if (currentStatus === 'FAILED') {
            clearInterval(interval);
            setIsScanning(false);
            setScanStatus('FAILED');
            setScanNotice('Crawl failed. Please verify the URL is publicly reachable.');
            setTimeout(() => setScanNotice(null), 5000);
          }
        } catch {
          // If polling endpoint times out, fallback gracefully
          clearInterval(interval);
          setIsScanning(false);
          await fetchProfile();
        }
      }, 3000);
    } catch (err: any) {
      console.error('Failed to start website scan:', err);
      setIsScanning(false);
      setScanNotice(err.response?.data?.detail || 'Failed to dispatch website crawler.');
      setTimeout(() => setScanNotice(null), 5000);
    }
  };

  // Save Profile Edits
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const res = await axios.put('/api/v1/business-profile', {
        company_name: editCompanyName.trim(),
        description: editDescription.trim(),
        pricing_model: editPricing.trim(),
      });
      setProfile(res.data);
      setIsEditing(false);
    } catch (err: any) {
      console.error('Failed to update profile:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // Perform Live pgvector RAG Search
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

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Website Intelligence &amp; Knowledge Base
          </h2>
        </div>

        {profile && (
          <SquircleButton
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-1.5 shadow-sm"
          >
            <Edit3 className="w-3.5 h-3.5" />
            Edit Knowledge Profile
          </SquircleButton>
        )}
      </div>

      {/* Notice Banner */}
      {scanNotice && (
        <FrostedGlassCard className="p-3.5 border-blue-200/80 bg-blue-50/60 text-xs text-blue-800 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            <span>{scanNotice}</span>
            {scanStatus && (
              <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold">
                {scanStatus}
              </span>
            )}
          </span>
          <button onClick={() => setScanNotice(null)} className="text-blue-500 hover:text-blue-700 font-bold">
            ✕
          </button>
        </FrostedGlassCard>
      )}

      {/* Loading Skeleton */}
      {isLoadingProfile ? (
        <FrostedGlassCard elevated className="p-16 flex flex-col items-center justify-center text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
          <div className="text-sm font-semibold text-[var(--text-primary)]">Loading Grounded Knowledge Base...</div>
          <div className="text-xs text-[var(--text-muted)]">Verifying source provenance and pgvector document embeddings</div>
        </FrostedGlassCard>
      ) : !profile ? (
        /* Empty State & Initial Website Crawler Input */
        <FrostedGlassCard elevated className="p-10 md:p-16 flex flex-col items-center justify-center text-center space-y-6">
          <div className="w-16 h-16 rounded-[24px] bg-[var(--accent-subtle)] border border-[var(--accent-border)] flex items-center justify-center text-[var(--accent-primary)] shadow-sm">
            <Globe className="w-8 h-8" />
          </div>

          <div className="max-w-md space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              No Grounded Business Profile Yet
            </h3>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Enter your corporate website URL below. Our Playwright crawler will automatically index your offerings, pricing, value propositions, and FAQs into vector embeddings for 0% hallucination SDR outreach.
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
              {isScanning ? 'Crawling...' : 'Scan Website'}
            </SquircleButton>
          </form>
        </FrostedGlassCard>
      ) : (
        /* Profile Active Overview & RAG Verification */
        <div className="space-y-6">
          {/* Top Profile Summary Card */}
          <FrostedGlassCard elevated className="p-6 md:p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 pb-6 border-b border-white/80">
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-xl font-bold text-[var(--text-primary)]">{profile.company_name}</h3>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Grounded &amp; Active (v{profile.version})
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] max-w-2xl leading-relaxed">
                  {profile.description || 'No company description provided.'}
                </p>
              </div>

              {profile.pricing_model && (
                <div className="p-3 rounded-[16px] bg-slate-50 border border-slate-200/80 shrink-0">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">
                    Grounded Pricing Structure
                  </span>
                  <span className="text-xs font-bold text-slate-800 font-mono">{profile.pricing_model}</span>
                </div>
              )}
            </div>

            {/* Target ICP Verticals & Value Propositions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[var(--accent-primary)]" />
                  Target Industry Verticals
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {profile.target_industries && profile.target_industries.length > 0 ? (
                    profile.target_industries.map((ind, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-[10px] text-xs font-semibold bg-[var(--accent-subtle)] text-[var(--accent-primary)] border border-[var(--accent-border)]"
                      >
                        {ind}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">No target verticals extracted.</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                  Core Value Propositions
                </h4>
                <div className="space-y-1.5">
                  {profile.value_propositions && profile.value_propositions.length > 0 ? (
                    profile.value_propositions.map((vp, i) => (
                      <div key={i} className="text-xs text-slate-700 flex items-start gap-2">
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{vp}</span>
                      </div>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">No value propositions recorded.</span>
                  )}
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
                className="shrink-0"
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
                        <span className="font-bold text-slate-800 truncate">{chk.document_title || 'Document'}</span>
                        <span className="px-2 py-0.5 rounded-[8px] bg-emerald-50 text-emerald-700 font-mono text-[10px] font-bold">
                          Similarity: {Math.round(chk.similarity_score * 100)}%
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
      )}

      {/* Edit Knowledge Profile Modal */}
      <SquircleModal
        isOpen={isEditing}
        onClose={() => setIsEditing(false)}
        title="Edit Knowledge Profile"
        maxWidth="xl"
      >
        <form onSubmit={handleSaveProfile} className="space-y-4 pt-1">
          <SquircleInput
            label="Company Name"
            value={editCompanyName}
            onChange={(e) => setEditCompanyName(e.target.value)}
            required
          />

          <SquircleTextarea
            label="Company Description"
            rows={3}
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
          />

          <SquircleInput
            label="Pricing Tiers / Policy Summary"
            value={editPricing}
            onChange={(e) => setEditPricing(e.target.value)}
            placeholder="e.g. Free Tier, Growth: $49/mo, Enterprise: Custom SLA"
          />

          <div className="pt-3 flex justify-end gap-3">
            <SquircleButton
              variant="outline"
              type="button"
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </SquircleButton>
            <SquircleButton
              variant="primary"
              type="submit"
              isLoading={isSaving}
            >
              Save Profile Changes
            </SquircleButton>
          </div>
        </form>
      </SquircleModal>
    </div>
  );
};
