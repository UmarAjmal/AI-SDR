# CODENTER AI SDR PLATFORM
## Comprehensive Production Implementation Milestones & Developer Execution Prompts
### Engineered by a 12+ Year Veteran Principal AI Systems & Full-Stack Architect
**Target Architecture:** FastAPI (Python 3.11+), PostgreSQL 16 + pgvector, Redis 7, Celery, React 18 + Vite + Tailwind CSS, Playwright, OAuth2 (Google, Microsoft, HubSpot).  
**Source Specification:** `Codenter_AI_SDR_Developer_Product_Specification.docx` (Version 1.0, September 2026)  
**Aesthetic & Frontend Philosophy:** Ultra-Clean White canvas, 3D Frosted Acrylic Glassmorphism, Dynamic Secondary Accent Engine (Default: Cobalt Blue `#1D4ED8` Drafting Engine, user-customizable), and Apple-Style Continuous Squircle Geometry applied to every interactive shape.

---

# Executive Audit & 100% Specification Compliance Matrix

Before breaking down the implementation, this architectural blueprint audits and incorporates every single section of the 31 chapters in the Developer Product Specification:

| Chapter & Scope | Specification Requirement | Verification & Milestone Mapping |
| :--- | :--- | :--- |
| **Ch. 1: Product Overview** | Autonomous sales workflow (not bulk spam); Golden Loop: Understand $\rightarrow$ Personalize $\rightarrow$ Schedule $\rightarrow$ Classify $\rightarrow$ Grounded Answer $\rightarrow$ Qualify $\rightarrow$ Book Meeting $\rightarrow$ CRM Sync. | **M1, M2, M3, M5, M6, M7, M8, M9** |
| **Ch. 1.2: Non-Goals** | No generic email client, no spam bursts, no hallucinating prices/terms, no blind auto-sends, no broad provider bloat in V1. | Embedded as deterministic code gates in **M4, M6, M7** |
| **Ch. 1.3: V1 Integrations** | HubSpot CRM, Google Workspace, Microsoft 365, Google Calendar, MS Calendar, BrandScan crawler, Provider-agnostic LLM Gateway. | Provider adapters in **M2, M3, M4, M6, M9** |
| **Ch. 2: User Journey** | 16-step end-to-end journey + Golden Path sequence. | End-to-End lifecycle modeled in **M5, M7, M9, M12** |
| **Ch. 3: Architecture** | 15 Modular services, FastAPI + Celery + pgvector + Redis, internal Model Gateway. | Architectural foundation in **M1, M6** |
| **Ch. 4: Website Intelligence** | 13-step crawl pipeline, Playwright fallback, 12-field Business Profile schema, source provenance, versioned chunks. | Comprehensive crawl and extraction engine in **M2** |
| **Ch. 5: CRM & Leads** | OAuth tokens encrypted at rest, 10 canonical lead groups, deterministic 0–100 scoring with explainable reasons. | Lead schema, HubSpot adapter, and scoring engine in **M3** |
| **Ch. 6: Campaign Engine** | 10 campaign config sections, 7 campaign states, 13 per-lead sequence states, 9 strict stop conditions. | Complete state machines and Celery Beat scheduler in **M5** |
| **Ch. 7: Personalization** | Bounded context packaging, structured JSON output contract, role adaptation, anti-hallucination rules. | Prompt engineering, Pydantic schemas, and claim filters in **M6** |
| **Ch. 8: Reply Handling** | 14-intent taxonomy, deterministic unsubscribe regex, grounded RAG replier, rolling conversation memory, handoff. | Inbound parser, classifier, and replier in **M7** |
| **Ch. 9: Qualification** | NFAT (Need, Fit, Authority, Timing) framework, 9-field structured qualification schema, CRM status sync. | Qualification agent and bi-directional sync in **M8** |
| **Ch. 10: Meeting Booking** | 9-step booking flow, prospect timezone conversion, 15-min buffers, race condition prevention, auto-stop sequence. | Slot finder, concurrency locks, and calendar adapters in **M9** |
| **Ch. 11: Email Deliverability** | Abstract `EmailProvider`, mailbox daily caps, randomized jitter pacing (120-300s), SPF/DKIM/DMARC checks, suppression list. | Sending pipeline, rate limiters, and bounce handlers in **M4** |
| **Ch. 12: Database Design** | 23 normalized tables, tenant isolation, workspace_id scoping, PostgreSQL row-level security. | Complete relational + vector schema in **M1, M10** |
| **Ch. 13: API Specification** | 18 core REST endpoints, 4 webhook classes with signature verification and strict idempotency. | FastAPI router contracts in **M1, M3, M4, M5, M7, M9, M10** |
| **Ch. 14: Background Jobs** | 12 Celery background tasks with retry policies, distributed Redis locking (`redlock`), UTC execution times. | Worker pipelines in **M1, M2, M4, M5, M7, M8, M9** |
| **Ch. 15: AI Architecture** | 8 specialized AI components, Model Gateway (fallback + telemetry), Hybrid RAG (pgvector + metadata filtering). | Multi-agent framework and gateway in **M6, M7, M8** |
| **Ch. 16: Guardrails & Handoff**| 10 risk scenarios with mandatory controls, Human-in-the-Loop Inbox. | Gating filters in **M6, M7** and UI in **M11** |
| **Ch. 17: Frontend / Dashboard**| 9 navigation areas, lead detail timeline, visual campaign wizard, DOMPurify HTML email sanitization. | Reusable component library and responsive web app in **M11** |
| **Ch. 18: Security & Privacy** | AES-256-GCM token encryption, RBAC, webhook HMAC verification, PII sanitization. | Security architecture in **M1, M3, M4, M11** |
| **Ch. 19: Observability** | 5-question audit logging trail, 8 operational telemetry metric areas. | Audit logging and event dispatcher in **M10** |
| **Ch. 20: Testing Strategy** | Unit tests, integration tests, AI eval benchmarks (100% unsubscribe recall assertion), 9 E2E scenarios. | Comprehensive test harness in **M12** |
| **Ch. 21: Deployment & Ops** | Multi-worker Docker topology (separate crawler from email worker), Nginx reverse proxy, Postgres connection pooling. | Production containerization in **M12** |
| **Ch. 22: Repository Structure**| Standard monorepo (`apps/`, `packages/`, `infra/`, `tests/`). | Monorepo layout in **M1** |
| **Ch. 23: BrandScan Reuse** | Reusable crawling, rendering, chunking, embeddings vs new SDR campaign/CRM/email modules. | Explicit package boundaries in **M2** |
| **Ch. 24: Development Phases** | 12 chronological phases including Interpulse AI voice handoff. | 1-to-1 mapped into Milestones 1 through 12 |
| **Ch. 25: MVP Criteria** | 18 verifiable MVP acceptance criteria. | Final acceptance validation in **M12** |
| **Ch. 26: Failure Matrix** | 12 failure edge cases (rate limits, token expiry, booking races, mid-flight pauses). | Handled across **M3, M4, M5, M7, M9, M12** |
| **Ch. 27: Analytics & Funnel** | 13 core metrics, 7-step conversion funnel. | Aggregation engine and visualizations in **M10, M11** |
| **Ch. 28: Future Roadmap** | Multi-channel, Interpulse voice handoff, buying committee mapping. | Architecture hooks in **M8, M12** |
| **Ch. 29–31: Principles & Refs**| Deterministic rules > LLM guesswork, idempotency, provenance, database as single source of truth. | Enforced across all 12 milestones |

---

# Global Frontend Design System: Apple Frosted Acrylic & Squircle Architecture

The frontend is constructed using an **Atomic Reusable Component Architecture** adhering to a distinct, ultra-premium aesthetic:
1. **Base Color Canvas:** Ultra-Clean Pristine White (`#FFFFFF`) with subtle frosted slate backing (`#F8FAFC`) and delicate border dividers (`#E2E8F0`).
2. **3D Frosted Acrylic Glassmorphism:** High-refraction translucent layers (`rgba(255, 255, 255, 0.72)` to `rgba(255, 255, 255, 0.88)`), heavy backdrop blur (`backdrop-blur-xl` 20px), subtle double borders (`border border-white/80`), and specular inner top highlights (`box-shadow: inset 0 1px 1px 0 rgba(255, 255, 255, 0.95)`).
3. **Dynamic Secondary Accent Engine:** Driven entirely by CSS custom properties. Defaults to **Cobalt Blue Drafting Engine** (`#1D4ED8` / `#2563EB`), with runtime theme switching allowing the user to select their desired secondary accent (Cobalt Blue, Electric Indigo, Emerald Precision, Cyber Violet, Sunset Amber).
4. **Apple Squircle Geometry:** Eliminates standard harsh rounded rectangles in favor of continuous curvature squircles (`border-radius: 20px; corner-smoothing: squircle;` / custom SVG clip-paths / Tailwind `@squircle` utilities) across all buttons, cards, dialogs, badges, and input controls.

### Dynamic CSS Variable System (`apps/web/src/index.css`)
```css
:root {
  /* Canvas Base */
  --bg-canvas: #FAFBFC;
  --bg-surface: #FFFFFF;
  --bg-surface-frosted: rgba(255, 255, 255, 0.75);
  --bg-surface-glass-heavy: rgba(255, 255, 255, 0.88);
  --border-glass: rgba(255, 255, 255, 0.80);
  --border-subtle: #E2E8F0;
  
  /* Text Layers */
  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #94A3B8;

  /* Default Dynamic Secondary Accent: Cobalt Blue Drafting Engine */
  --accent-primary: #1D4ED8;
  --accent-hover: #1E40AF;
  --accent-subtle: #EFF6FF;
  --accent-glow: rgba(29, 78, 216, 0.22);
  --accent-border: rgba(29, 78, 216, 0.35);

  /* 3D Acrylic Specular & Shadow Tokens */
  --shadow-glass: 0 10px 25px -5px rgba(15, 23, 42, 0.04), 0 8px 10px -6px rgba(15, 23, 42, 0.03);
  --shadow-glass-elevated: 0 20px 35px -10px rgba(15, 23, 42, 0.08), 0 10px 15px -5px rgba(15, 23, 42, 0.04);
  --specular-highlight: inset 0 1px 1px 0 rgba(255, 255, 255, 0.95);
  --specular-accent: inset 0 1px 1px 0 rgba(255, 255, 255, 0.35);

  /* Continuous Squircle Radius Tokens */
  --squircle-sm: 12px;
  --squircle-md: 18px;
  --squircle-lg: 24px;
  --squircle-xl: 32px;
}

/* User-Selectable Accent Theme Classes */
[data-accent="indigo"] {
  --accent-primary: #4F46E5;
  --accent-hover: #4338CA;
  --accent-subtle: #EEF2FF;
  --accent-glow: rgba(79, 70, 229, 0.22);
  --accent-border: rgba(79, 70, 229, 0.35);
}
[data-accent="emerald"] {
  --accent-primary: #059669;
  --accent-hover: #047857;
  --accent-subtle: #ECFDF5;
  --accent-glow: rgba(5, 150, 105, 0.22);
  --accent-border: rgba(5, 150, 105, 0.35);
}
[data-accent="violet"] {
  --accent-primary: #7C3AED;
  --accent-hover: #6D28D9;
  --accent-subtle: #F5F3FF;
  --accent-glow: rgba(124, 58, 237, 0.22);
  --accent-border: rgba(124, 58, 237, 0.35);
}
[data-accent="amber"] {
  --accent-primary: #D97706;
  --accent-hover: #B45309;
  --accent-subtle: #FFFBEB;
  --accent-glow: rgba(217, 119, 6, 0.22);
  --accent-border: rgba(217, 119, 6, 0.35);
}
```

---

# Reusable Component Architecture Library (`apps/web/src/components/ui/`)

Every visual element is encapsulated into reusable, composable, strongly typed React components:

1. **`SquircleButton`** (`SquircleButton.tsx`):
   * Curvature: Smooth Apple Squircle (`rounded-[18px]`).
   * Variants:
     * `primary`: Dynamic accent background (`var(--accent-primary)`), white text, specular top highlight (`var(--specular-accent)`), glow shadow on hover (`var(--accent-glow)`).
     * `frosted`: 3D frosted acrylic (`bg-white/80 backdrop-blur-md border border-white/80 text-slate-800`), inner specular highlight.
     * `outline`: Subtle border (`border-slate-200 hover:border-[var(--accent-primary)] hover:bg-[var(--accent-subtle)]`).
     * `ghost`: Transparent with soft hover highlight.
     * `danger`: Rose acrylic (`bg-rose-500 text-white`).
   * Micro-animations: `active:scale-[0.98] transition-all duration-200 ease-out`.

2. **`FrostedGlassCard`** (`FrostedGlassCard.tsx`):
   * Surface: `bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)]`.
   * Highlights: Top specular reflection `shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.95)]`.
   * Corners: Continuous squircle (`rounded-[24px]`).

3. **`SquircleInput` & `SquircleTextarea`** (`SquircleInput.tsx`):
   * Background: Translucent white `bg-white/70 backdrop-blur-md border border-slate-200/80`.
   * Focus State: Border color transitions to `var(--accent-primary)` with glowing ring `ring-4 ring-[var(--accent-glow)]`.
   * Corners: `rounded-[16px]`.

4. **`GlassBadge` & `IntentBadge`** (`IntentBadge.tsx`):
   * 14 distinct intent visual variants (`POSITIVE_INTEREST`, `PRICING`, `PRODUCT_QUESTION`, `OBJECTION`, `UNSUBSCRIBE`, etc.).
   * Translucent frosted pill with squircle curvature (`rounded-[12px]`), subtle matching border, and glowing dot indicator.

5. **`SquircleModal` & `SquircleDrawer`** (`SquircleModal.tsx`):
   * Backdrop: Multi-layer blur (`backdrop-blur-md bg-slate-900/20`).
   * Dialog: Floating 3D frosted acrylic container (`bg-white/90 backdrop-blur-2xl rounded-[32px] border border-white shadow-2xl p-6`).

6. **`ICPScoreGauge`** (`ICPScoreGauge.tsx`):
   * Circular or radial progress meter (0–100) rendered with dynamic accent stroke.
   * Color bands: HOT (80-100: Emerald), WARM (50-79: Cobalt/Dynamic Accent), COLD (0-49: Slate).
   * Expandable popover showing structured score reasons.

7. **`SplitPaneInbox`** (`SplitPaneInbox.tsx`):
   * Resizable dual-pane container: Left pane displays conversation list with intent badges; Right pane renders full email thread with collapsible AI reasoning and grounded knowledge citations.

8. **`ThemePicker`** (`ThemePicker.tsx`):
   * Sleek squircle dropdown allowing the user to switch the secondary accent color live at runtime (Cobalt, Indigo, Emerald, Violet, Amber).

---

# Milestone 1: Core Multi-Tenant Foundation, Database Schema & Architecture Skeleton

### 1. Milestone Scope & Objective
Establish the production-ready monorepo structure, PostgreSQL 16 + `pgvector` database schema, Alembic migration pipeline, JWT/Session authentication with RBAC, multi-tenant workspace isolation enforcement, and Redis/Celery background task execution framework.

### 2. Detailed Technical Specifications & Deliverables
* **Repository Architecture:** Monorepo folders: `apps/api`, `apps/worker`, `apps/web`, `packages/common`, `packages/ai`, `packages/crm`, `packages/email`, `packages/calendar`, `packages/campaign`, `packages/lead_intelligence`, `packages/compliance`, `infra/docker`, `infra/migrations`.
* **Database Models (SQLAlchemy 2.0 async):**
  * `users` (`id`, `email`, `hashed_password`, `status`, `created_at`, `updated_at`)
  * `workspaces` (`id`, `name`, `slug`, `domain`, `settings_json`, `created_at`)
  * `workspace_members` (`workspace_id`, `user_id`, `role`: `OWNER`, `ADMIN`, `MEMBER`, `READONLY`)
  * `audit_logs` (`id`, `workspace_id`, `actor_id`, `actor_type`, `action`, `resource_type`, `resource_id`, `payload`, `ip_address`, `created_at`)
  * `usage_events` (`id`, `workspace_id`, `event_type`, `units`, `cost_estimate_usd`, `metadata_json`, `created_at`)
* **Multi-Tenant Security Enforcement:** FastAPI dependency `get_current_workspace_context` that extracts workspace claims from JWT/Session and automatically attaches `workspace_id` filters to all ORM queries. Never trust client-supplied `workspace_id`.
* **Distributed Async Skeleton:** Celery app setup with Redis broker/result backend, dead-letter exchange (DLX), task retry policies with exponential backoff and jitter.

### 3. Edge Cases & Critical Safeguards
* Data leak across tenants: Enforce foreign key cascade rules and PostgreSQL schema/RLS considerations.
* Worker context: Background Celery jobs must serialize and deserialize explicit `workspace_id` metadata.

---

### 🟢 Master Production Execution Prompt: Milestone 1

```markdown
### PROMPT: MILESTONE 1 - CORE MULTI-TENANT FOUNDATION & DISTRIBUTED SKELETON

You are a 12+ Year Veteran Principal AI Systems and Backend Architect. Your objective is to build Milestone 1 of the Codenter AI SDR Platform strictly adhering to the "Codenter AI SDR Developer Product Specification".

#### 1. Directory Structure Setup
Initialize the project monorepo structure:
- `apps/api/` (FastAPI 0.110+ application)
- `apps/worker/` (Celery 5.4+ distributed worker process)
- `apps/web/` (React 18 + Vite + Tailwind CSS frontend)
- `packages/common/` (Database models, config, encryption, schemas)
- `packages/compliance/` (Suppression and audit utilities)
- `infra/docker/` (Docker Compose for Postgres 16 with pgvector, Redis 7)
- `infra/migrations/` (Alembic migration scripts)

#### 2. Infrastructure & Database Schema (PostgreSQL 16 + pgvector)
Create Docker Compose with:
- `postgres`: `pgvector/pgvector:pg16` with healthcheck, persistent volume.
- `redis`: `redis:7-alpine` with persistent AOF.
Implement SQLAlchemy 2.0 Async declarative models in `packages/common/models/`:
1. `User`: `id` (UUID), `email` (unique, indexed), `hashed_password`, `status` (ACTIVE, SUSPENDED), `created_at`, `updated_at`.
2. `Workspace`: `id` (UUID), `name`, `domain`, `settings` (JSONB), `created_at`, `updated_at`.
3. `WorkspaceMember`: `id` (UUID), `workspace_id` (FK), `user_id` (FK), `role` (ENUM: OWNER, ADMIN, MEMBER, READONLY), unique constraint on (`workspace_id`, `user_id`).
4. `AuditLog`: `id` (UUID), `workspace_id` (FK, indexed), `actor_id` (UUID), `actor_email` (VARCHAR), `action` (VARCHAR), `resource_type` (VARCHAR), `resource_id` (VARCHAR), `payload` (JSONB), `created_at` (TIMESTAMPTZ, indexed).
5. `UsageEvent`: `id` (UUID), `workspace_id` (FK, indexed), `event_type` (ENUM: MODEL_TOKENS, EMAIL_SENT, BROWSER_RENDER, ENRICHMENT_CALL), `units` (INTEGER), `cost_estimate_usd` (NUMERIC(10,6)), `metadata_json` (JSONB), `created_at` (TIMESTAMPTZ, indexed).

#### 3. Security, Authentication & Tenant Isolation
In `apps/api/core/`:
- Implement Argon2id password hashing and PyJWT token generation (15-min access token, 7-day refresh token in encrypted HttpOnly cookie).
- Implement an authentication dependency `get_current_user` and tenant isolation dependency `get_current_workspace_context`.
- CRITICAL ARCHITECTURAL RULE: Every database query accessing tenant data must automatically enforce `workspace_id == current_workspace.id`. Never allow client queries to override the workspace context.
- Implement RBAC permission decorator `@require_role(["OWNER", "ADMIN"])`.

#### 4. Asynchronous Task Worker Pipeline (Celery + Redis)
In `apps/worker/`:
- Configure Celery with Redis broker and Redis backend.
- Define dedicated queues: `default`, `email_send`, `crawler`, `ai_tasks`, `sync`.
- Implement exponential backoff retry decorator with randomized jitter for all tasks.
- Create an audit and correlation context middleware that injects `workspace_id` and `trace_id` into all asynchronous job logs.

#### 5. Verification & Acceptance Criteria
- Run Alembic migration to create all tables cleanly including vector extension (`CREATE EXTENSION IF NOT EXISTS vector;`).
- Write unit tests (`tests/unit/test_auth.py`, `tests/unit/test_tenant_isolation.py`) verifying:
  a. User registration, login, token refresh.
  b. User from Workspace A cannot query, update, or delete records belonging to Workspace B (returns 403/404).
  c. Celery worker boots and successfully executes a test background task with tenant context.
```

---

# Milestone 2: Website Intelligence, Browser Crawling & Grounded Knowledge Base

### 1. Milestone Scope & Objective
Implement the autonomous Website Intelligence scan module (reusing the Codenter BrandScan architecture). Turn any corporate website URL into a verified, structured Business Profile, extract verifiable facts with source provenance, render JavaScript-heavy web applications via Playwright, and chunk/embed content into PostgreSQL `pgvector` for grounded RAG retrieval.

### 2. Detailed Technical Specifications & Deliverables
* **Crawl Pipeline Execution (13 Sequential Steps):**
  1. Validate URL & normalize domain.
  2. Parse `robots.txt` and obey crawl politeness policies.
  3. Inspect `sitemap.xml` and discover internal URLs.
  4. Prioritize high-value pages: Home, Product/Services, Pricing, About, Industries, Use Cases, Case Studies, FAQs, Contact, Docs, Legal/Policy.
  5. Static HTTP fetch (via `httpx`) with automatic fallback to headless Playwright browser rendering for single-page applications (React/Next/Vue).
  6. Extract structured facts while stripping navigation menus, footers, cookie banners, and scripts.
* **Database Models:**
  * `business_profiles` (`id`, `workspace_id`, `company_name`, `legal_name`, `summary`, `offerings`, `value_propositions`, `industries`, `icp_hints`, `pricing_data`, `features_catalog`, `faqs`, `proof_points`, `brand_voice`, `claims_policy`, `ctas`, `version`, `confidence_score`, `created_at`, `updated_at`)
  * `knowledge_documents` (`id`, `workspace_id`, `url`, `title`, `http_status`, `content_hash`, `source_type`, `screenshot_path`, `raw_text`, `fetched_at`)
  * `knowledge_chunks` (`id`, `workspace_id`, `document_id`, `chunk_index`, `content`, `token_count`, `embedding` vector(1536), `metadata_json`, `created_at`)
* **Knowledge Provenance & Freshness Rules:**
  * Every extracted fact MUST store its `source_url` and `extraction_timestamp`.
  * Pricing, legal guarantees, and feature limits must store freshness tags and never be fabricated.

### 3. Edge Cases & Critical Safeguards
* Cloudflare/Bot-blocking: Use browser stealth headers and reasonable rate delays.
* Unreachable/Broken URLs: Mark scan as `PARTIAL_FAILURE` with page coverage metrics; NEVER invent fake company information.
* Hallucination Prevention: If pricing is not publicly stated on the website, mark pricing as `CONTACT_SALES` or `UNAVAILABLE`. Never extrapolate pricing numbers.

---

### 🟢 Master Production Execution Prompt: Milestone 2

```markdown
### PROMPT: MILESTONE 2 - WEBSITE INTELLIGENCE, CRAWLER & GROUNDED KNOWLEDGE BASE

You are a 12+ Year Veteran Principal AI Systems and Web Scraping Engineer. Your objective is to implement Milestone 2 of the Codenter AI SDR Platform strictly following Section 4 and Section 23 of the Product Specification.

#### 1. Data Models (SQLAlchemy + pgvector)
In `packages/common/models/knowledge.py`:
1. `BusinessProfile`:
   - `id`: UUID (PK), `workspace_id`: UUID (FK, unique per active version)
   - `company_name`: VARCHAR, `legal_name`: VARCHAR, `description`: TEXT
   - `offerings`: JSONB (products, services, tiers)
   - `value_propositions`: JSONB (benefits, differentiators)
   - `industries`: JSONB (array of target verticals)
   - `icp_hints`: JSONB (company sizes, personas, locations)
   - `pricing`: JSONB (pricing models, public rates, or null if gated)
   - `features`: JSONB (catalog of features)
   - `faqs`: JSONB (extracted Q&As)
   - `proof`: JSONB (case studies, metrics, customer logos with source citations)
   - `brand_voice`: JSONB (tone keywords, formality rating, stylistic rules)
   - `claims_policy`: JSONB (allowed statements, forbidden statements, mandatory disclaimers)
   - `ctas`: JSONB (primary and secondary call-to-actions)
   - `version`: INTEGER, `is_active`: BOOLEAN, `updated_at`: TIMESTAMPTZ
2. `KnowledgeDocument`:
   - `id`: UUID (PK), `workspace_id`: UUID (FK), `url`: TEXT, `title`: TEXT, `content_hash`: VARCHAR(64), `source_type`: VARCHAR, `raw_text`: TEXT, `screenshot_url`: TEXT, `fetched_at`: TIMESTAMPTZ
3. `KnowledgeChunk`:
   - `id`: UUID (PK), `workspace_id`: UUID (FK), `document_id`: UUID (FK), `chunk_index`: INT, `content`: TEXT, `embedding`: Vector(1536), `metadata_json`: JSONB (includes source_url, page_type, extracted_at), `created_at`: TIMESTAMPTZ

#### 2. Robust Web Crawling & Playwright Engine
In `packages/website_intelligence/`:
- Implement `URLNormalizer`: Normalize protocols, strip tracking parameters (`utm_*`), validate valid HTTP/HTTPS domain.
- Implement `RobotsParser`: Fetch `robots.txt`, respect User-Agent rules and crawl delays.
- Implement `SitemapCrawler`: Parse `sitemap.xml` for URL discovery; prioritize high-value paths (`/about`, `/pricing`, `/product`, `/services`, `/case-studies`, `/faq`, `/contact`).
- Implement `HybridPageFetcher`:
  1. Try fast asynchronous HTTP GET using `httpx` with realistic browser headers.
  2. If page contains JavaScript framework shells (`<div id="root"></div>`, minimal text content), route URL to the `PlaywrightRenderer` worker.
  3. Playwright worker runs headless Chromium, waits for `networkidle`, takes full-page screenshot, and extracts clean DOM HTML.
- Implement `ContentCleaner`: Use `trafilatura` or `BeautifulSoup4` to strip `<header>`, `<footer>`, `<nav>`, `<aside>`, cookie notices, and ads. Extract hierarchical markdown.

#### 3. Fact Extraction & Structured Profile Generation
In `packages/ai/extractors/business_extractor.py`:
- Feed cleaned text into an LLM call using OpenAI/Anthropic with strict Pydantic structured output matching the `BusinessProfile` schema.
- Enforce strict provenance: Every fact must point to the specific URL where it was found.
- If pricing or claims are missing or ambiguous, output `null` or flag `requires_human_review: true`.
- Implement semantic chunker (500–800 tokens with 100-token overlap) and compute embeddings using `text-embedding-3-small` (1536 dims). Store in `knowledge_chunks` table with pgvector HNSW index (`vector_cosine_ops`).

#### 4. REST Endpoints & Celery Tasks
- `POST /api/v1/website-scans`: Initiates crawl task in background (`tasks.run_website_scan.delay(workspace_id, url)`). Returns scan tracking ID.
- `GET /api/v1/website-scans/{id}`: Returns progress, pages crawled, pages failed, and current extraction status.
- `GET /api/v1/business-profile`: Retrieves current active profile.
- `PUT /api/v1/business-profile`: Allows human user to edit, correct, or override extracted facts.

#### 5. Verification & Tests
- Integration tests using a mocked HTTP server:
  a. Crawl multi-page mock site and populate `KnowledgeDocument` and `KnowledgeChunk`.
  b. Verify vector search returns the most relevant chunk for a query like "What is the refund policy?".
  c. Verify that if a page is blocked, the scan completes partially without hallucinating or crashing.
```

---

# Milestone 3: CRM Integration, Field Mapping & Canonical Lead Intelligence Engine

### 1. Milestone Scope & Objective
Build the CRM integration subsystem starting with HubSpot (and architected for Salesforce/Pipedrive via provider adapters). Support OAuth2 token exchange with encrypted token persistence, field-level mapping, bidirectional synchronization, lead deduplication, and a deterministic 0–100 lead scoring engine.

### 2. Detailed Technical Specifications & Deliverables
* **Provider Adapter Pattern:** Common `CRMProvider` abstract base class:
  * `get_authorization_url()`, `exchange_code_for_tokens()`, `refresh_access_token()`
  * `import_contacts(cursor, filters)`, `get_contact_by_id()`, `update_contact_fields(contact_id, payload)`
  * `register_webhook()`, `parse_webhook_payload()`
* **Database Models:**
  * `crm_connections` (`id`, `workspace_id`, `provider`: `HUBSPOT`, `account_id`, `encrypted_access_token`, `encrypted_refresh_token`, `token_expires_at`, `field_mappings_json`, `sync_status`, `last_sync_at`)
  * `crm_leads` (Canonical schema: `id`, `workspace_id`, `crm_connection_id`, `crm_record_id`, `first_name`, `last_name`, `email`, `phone`, `job_title`, `company_name`, `domain`, `industry`, `employee_count`, `location`, `revenue_band`, `lifecycle_stage`, `owner_id`, `lead_notes`, `custom_fields`, `opt_out`, `do_not_contact`, `bounce_status`, `icp_score`, `intent_score`, `total_score`, `score_reasons_json`, `created_at`, `updated_at`)
  * `lead_enrichment` (`id`, `workspace_id`, `lead_id`, `company_summary`, `role_summary`, `detected_technologies`, `signals_json`, `source_urls`, `enriched_at`)
* **Deterministic Lead Scoring Algorithm (0 to 100):**
  * ICP Fit: `0 to 40` (Industry, size, geography, job title seniority)
  * Business Relevance: `0 to 25` (Problem/need alignment with business profile)
  * Intent Signals: `0 to 20` (Engagement, previous replies, timeline)
  * Data Quality: `0 to 10` (Corporate verified email and domain)
  * Negative Deductions: `0 to -20` (Competitors, personal emails like @gmail.com, out-of-scope roles)

### 3. Edge Cases & Critical Safeguards
* Token Expiration: Automatic refresh before API calls; if refresh token is revoked, pause sync and flag user immediately.
* Deduplication: Match leads strictly on normalized email (lowercase, trimmed). If email exists, update record without duplicating.
* Suppression Respect: If CRM contact has `unsubscribed` or `do_not_contact` set to true, propagate to canonical lead model immediately.

---

### 🟢 Master Production Execution Prompt: Milestone 3

```markdown
### PROMPT: MILESTONE 3 - CRM INTEGRATION, FIELD MAPPING & CANONICAL LEAD ENGINE

You are a 12+ Year Veteran Enterprise Integrations Architect. Your goal is to construct Milestone 3 of the Codenter AI SDR Platform according to Section 5 of the Product Specification.

#### 1. CRM Provider Abstraction
In `packages/crm/`:
- Create `base.py` defining abstract class `CRMProvider`:
  ```python
  class CRMProvider(ABC):
      @abstractmethod
      def get_auth_url(self, state: str) -> str: ...
      @abstractmethod
      async def exchange_code(self, code: str) -> TokenBundle: ...
      @abstractmethod
      async def refresh_tokens(self, refresh_token: str) -> TokenBundle: ...
      @abstractmethod
      async def fetch_contacts(self, access_token: str, cursor: Optional[str] = None, limit: int = 100) -> ContactBatch: ...
      @abstractmethod
      async def update_contact(self, access_token: str, contact_id: str, fields: dict) -> bool: ...
  ```
- Implement `packages/crm/adapters/hubspot_adapter.py`: Full implementation using HubSpot CRM v3 API (`/crm/v3/objects/contacts`). Handle rate limits (100 req/10 sec) with token-bucket rate limiter and retry.

#### 2. Encrypted Token Storage & Database Models
In `packages/common/models/crm.py`:
- Implement `CRMConnection` and `CRMLead` models.
- Implement AES-256-GCM symmetric encryption for OAuth tokens using `cryptography.fernet.Fernet`. Never store plain OAuth tokens in the database.
- Unique constraint on `CRMLead`: `(workspace_id, email)` to strictly prevent duplicate lead rows across imports.

#### 3. Field Mapping & Lead Normalization Engine
In `packages/crm/normalizer.py`:
- Map heterogeneous CRM fields into Canonical Lead Schema:
  - First Name, Last Name, Email, Job Title, Phone.
  - Company Name, Domain (extracted from email if missing), Industry, Employee Range.
  - CRM Lifecycle Stage, Owner ID.
- Store unmapped vendor attributes in `custom_fields` (JSONB).

#### 4. Deterministic Explainable Lead Scoring (0–100)
In `packages/lead_intelligence/scorer.py`:
- Implement `evaluate_lead_score(lead: CRMLead, profile: BusinessProfile) -> ScoreResult`:
  1. ICP Fit (0-40 pts): Exact match on target industries (+15), target company size (+15), target persona/job title keywords (+10).
  2. Business Relevance (0-25 pts): Company description matches offerings (+25).
  3. Intent (0-20 pts): Known trigger events or previous interactions.
  4. Data Quality (0-10 pts): Corporate MX domain (+10). Deduct for free email providers (-10).
  5. Negative Signals (-20 to 0 pts): Competitor domain match (-20), student/intern role (-15).
  - Return `total_score` (clamped 0 to 100), `score_band` (HOT: 80-100, WARM: 50-79, COLD: 0-49), and structured `reasons`: `list[ScoreReason]`.

#### 5. REST Endpoints & Webhooks
- `POST /api/v1/integrations/crm/{provider}/connect`: Generates CSRF state and returns OAuth redirect URL.
- `GET /api/v1/integrations/crm/{provider}/callback`: Exchanges code for tokens, encrypts tokens, persists `CRMConnection`.
- `POST /api/v1/leads/import`: Triggers asynchronous Celery task `tasks.sync_crm_leads.delay(workspace_id, connection_id)`.
- `GET /api/v1/leads`: Paginated lead list with filtering by score band, company, industry, and status.
- `GET /api/v1/leads/{id}`: Detailed lead profile with score breakdown and activity timeline.

#### 6. Verification & Automated Tests
- Unit test token encryption and decryption.
- Unit test the scoring engine against 5 test lead fixtures. Verify score reasons are returned as structured objects.
- Integration test with HubSpot mock API verifying contact pagination and deduplication on email.
```

---

# Milestone 4: Email Infrastructure, Provider Adapters & Deliverability Engine

### 1. Milestone Scope & Objective
Implement enterprise-grade outbound email sending and inbound parsing infrastructure. Build provider adapters for Google Workspace (Gmail API) and Microsoft 365 (Microsoft Graph API). Implement strict deliverability controls: per-mailbox daily caps, randomized jitter pacing, domain health checks, bounce handling, and automated suppression lists.

### 2. Detailed Technical Specifications & Deliverables
* **Provider Abstraction:** Abstract class `EmailProvider`:
  * `connect_oauth()`, `refresh_tokens()`
  * `send_email(account_id, to_email, subject, html_body, text_body, headers, thread_id)`
  * `get_message(message_id)`, `list_inbound_messages(since_timestamp)`
  * `watch_mailbox(webhook_url)` (Google Cloud Pub/Sub or Graph Subscription)
* **Database Models:**
  * `email_accounts` (`id`, `workspace_id`, `provider`: `GOOGLE` / `MICROSOFT`, `email_address`, `encrypted_credentials`, `daily_send_limit`, `current_day_sends`, `last_send_at`, `health_status`: `HEALTHY`, `PAUSED`, `REVOKED`, `created_at`)
  * `email_threads` (`id`, `workspace_id`, `lead_id`, `campaign_id`, `subject`, `status`: `OPEN`, `REPLIED`, `CLOSED`, `summary`, `last_message_at`, `created_at`)
  * `email_messages` (`id`, `workspace_id`, `thread_id`, `provider_message_id`, `direction`: `OUTBOUND` / `INBOUND`, `from_address`, `to_address`, `subject`, `body_text`, `body_html`, `headers_json`, `delivery_status`: `PENDING`, `SENT`, `DELIVERED`, `BOUNCED`, `created_at`)
  * `suppression_list` (`id`, `workspace_id`, `email`, `domain`, `reason`: `UNSUBSCRIBE`, `HARD_BOUNCE`, `COMPLAINT`, `MANUAL`, `created_at`)
* **Deliverability Controls & Randomized Jitter:**
  * Strict daily sending limits per mailbox (e.g. 30–50 cold emails/day).
  * Outbound queue spacing: Never send in bursts. Calculate randomized sleep intervals (e.g. 120s to 300s) between sends.
  * Re-check suppression list and campaign status immediately before issuing the provider API call.

### 3. Edge Cases & Critical Safeguards
* Stale Mailbox Authentication: If Google/Microsoft returns 401 Unauthorized, automatically set mailbox `health_status = REVOKED`, halt all pending sends for this mailbox, and notify the user.
* Double-Sending Prevention: Use a Redis distributed lock (`redlock`) keyed on `send_lock:{workspace_id}:{lead_id}` before dispatching an email.

---

### 🟢 Master Production Execution Prompt: Milestone 4

```markdown
### PROMPT: MILESTONE 4 - EMAIL SENDING, INBOUND INFRASTRUCTURE & DELIVERABILITY

You are a 12+ Year Veteran Email Deliverability and Protocol Engineer. Your objective is to build Milestone 4 of the Codenter AI SDR Platform matching Section 11 of the Product Specification.

#### 1. Provider Adapters (Google Workspace & Microsoft 365)
In `packages/email/`:
- Create `base.py` with abstract class `EmailProvider`:
  ```python
  class EmailProvider(ABC):
      @abstractmethod
      async def send_message(self, credentials: dict, message: OutboundEmail) -> SendResult: ...
      @abstractmethod
      async def fetch_message(self, credentials: dict, provider_msg_id: str) -> InboundEmail: ...
      @abstractmethod
      async def setup_webhook(self, credentials: dict, callback_url: str) -> bool: ...
  ```
- Implement `packages/email/adapters/gmail_adapter.py`: Uses Google API Client (`gmail/v1/users/me/messages/send`). Correctly format RFC 2822 raw MIME messages (base64url encoded), setting `Message-ID`, `In-Reply-To`, `References`, and `Subject`.
- Implement `packages/email/adapters/graph_adapter.py`: Uses Microsoft Graph API (`/v1.0/me/sendMail`). Include proper MIME threading headers.

#### 2. Models & Suppression Architecture
In `packages/common/models/email.py`:
- Define `EmailAccount`, `EmailThread`, `EmailMessage`, and `SuppressionList`.
- Add unique index on `suppression_list(workspace_id, email)`.
- Implement helper function `is_email_suppressed(workspace_id: UUID, email: str) -> bool` checking exact email address and domain level wildcards (e.g. `@competitor.com`).

#### 3. Concurrency-Safe Sending Pipeline
In `apps/worker/tasks/send_email.py`:
- Implement `send_campaign_email_task(campaign_lead_id: UUID)`:
  1. Acquire Redis lock on `lead_lock:{lead_id}` (TTL 30s).
  2. Verify:
     a. Lead is NOT suppressed in `suppression_list`.
     b. Campaign is currently in `RUNNING` state.
     c. Mailbox has not exceeded `daily_send_limit`.
     d. No prior email has been sent for this sequence step (idempotency check).
  3. Select healthy mailbox associated with campaign.
  4. Render email content and call `provider.send_message()`.
  5. Store provider message ID and thread references in `email_messages`.
  6. Increment mailbox send counter and record `next_action_at` for subsequent sequence steps.
  7. Release lock.
- On provider rate limit (HTTP 429), schedule Celery retry with exponential backoff and jitter.

#### 4. Inbound MIME Parsing & Threading Engine
In `packages/email/parser.py`:
- Implement inbound email parser that cleans raw email text, extracts sender headers, strips nested quote history, and attaches the incoming email to the existing `EmailThread` via `References` or `In-Reply-To` headers.

#### 5. Verification & Deliverability Tests
- Unit test RFC 2822 MIME generation ensuring threading headers match parent email.
- Unit test suppression check: Ensure suppressed email is aborted before provider call.
- Test Redis concurrency lock: Ensure two simultaneous Celery tasks for the same lead result in only ONE email sent.
```

---

# Milestone 5: Campaign Orchestration, State Machines & Distributed Scheduler

### 1. Milestone Scope & Objective
Construct the campaign sequence builder, the deterministic Campaign State Machine, and the per-lead Sequence State Machine. Build the distributed scheduler using Celery Beat and Redis to release outbound emails during the prospect's business hours while strictly honoring all stop conditions.

### 2. Detailed Technical Specifications & Deliverables
* **Campaign Configuration:**
  * Audience filters (ICP score range, target industries).
  * Objective (Demo booking, discovery call, trial signup).
  * Multi-step sequence steps (e.g. Step 1: Cold Intro -> Wait 3 business days -> Step 2: Value Proof -> Wait 4 business days -> Step 3: Breakup).
  * Business hour constraints: Allowed days (Mon-Fri) and hours (9 AM - 5 PM) calculated in the recipient's timezone.
* **Database Models:**
  * `campaigns` (`id`, `workspace_id`, `name`, `status`: `DRAFT`, `REVIEW`, `SCHEDULED`, `RUNNING`, `PAUSED`, `COMPLETED`, `ARCHIVED`, `objective`, `config_json`, `created_at`, `updated_at`)
  * `campaign_steps` (`id`, `campaign_id`, `step_number`, `delay_days`, `delay_hours`, `prompt_instructions`, `template_config_json`, `created_at`)
  * `campaign_leads` (`id`, `workspace_id`, `campaign_id`, `lead_id`, `current_step_number`, `state`: `QUEUED`, `WAITING`, `READY`, `SENT`, `REPLIED`, `PAUSED`, `UNSUBSCRIBED`, `BOUNCED`, `MEETING_BOOKED`, `QUALIFIED`, `DISQUALIFIED`, `HANDOFF`, `COMPLETED`, `next_action_at`, `updated_at`)
* **Deterministic Stop Conditions (9 Instant Halts):**
  1. Inbound reply received.
  2. Explicit opt-out / unsubscribe signal.
  3. Hard bounce or suppression.
  4. Meeting booked.
  5. Manual lead pause or deletion.
  6. CRM lifecycle status indicates active deal.
  7. Human handoff requested.
  8. Maximum sequence steps reached.
  9. Compliance block.

### 3. Edge Cases & Critical Safeguards
* Timezone Drift: Calculate business hours dynamically using the lead's detected timezone (e.g. `America/New_York`), falling back to workspace default if unknown.
* Scheduler Race Conditions: When the scheduler wakes up, it atomically claims eligible leads (`UPDATE campaign_leads SET state = 'READY' WHERE state = 'WAITING' AND next_action_at <= NOW() RETURNING id`).

---

### 🟢 Master Production Execution Prompt: Milestone 5

```markdown
### PROMPT: MILESTONE 5 - CAMPAIGN STATE MACHINE & DISTRIBUTED SCHEDULER

You are a 12+ Year Veteran Distributed Systems and Workflow Architect. Your objective is to construct Milestone 5 of the Codenter AI SDR Platform according to Section 6 and Section 14 of the Product Specification.

#### 1. Data Models & State Enums
In `packages/common/models/campaign.py`:
- Implement `Campaign`, `CampaignStep`, and `CampaignLead` models.
- Implement strict Enums:
  - `CampaignState`: `DRAFT`, `REVIEW`, `SCHEDULED`, `RUNNING`, `PAUSED`, `COMPLETED`, `ARCHIVED`.
  - `LeadSequenceState`: `QUEUED`, `WAITING`, `READY`, `SENT`, `REPLIED`, `PAUSED`, `UNSUBSCRIBED`, `BOUNCED`, `MEETING_BOOKED`, `QUALIFIED`, `DISQUALIFIED`, `HANDOFF`, `COMPLETED`.

#### 2. Deterministic State Machine Engine
In `packages/campaign/state_machine.py`:
- Implement `transition_lead_state(campaign_lead_id: UUID, new_state: LeadSequenceState, reason: str)`:
  - Enforce valid state transition matrix.
  - If transitioned to a terminal state (`UNSUBSCRIBED`, `BOUNCED`, `MEETING_BOOKED`, `COMPLETED`, `HANDOFF`), set `next_action_at = NULL` and purge any pending Celery send tasks.
  - Record transition in `conversation_events` table for complete auditability.

#### 3. Timezone & Business Hours Calculator
In `packages/campaign/scheduler.py`:
- Implement `calculate_next_send_time(lead_timezone: str, delay_days: int, send_window_start_hour: int = 9, send_window_end_hour: int = 17) -> datetime`:
  - Calculate strictly in UTC while respecting the recipient's local timezone.
  - Skip weekends (Saturday and Sunday).
  - Add randomized jitter (e.g. 5 to 45 minutes) so sends do not fire on exact round hours.

#### 4. Periodic Celery Beat Scheduler Task
In `apps/worker/tasks/scheduler_tasks.py`:
- Implement `evaluate_campaign_schedules_task()`:
  - Runs every 60 seconds via Celery Beat.
  - Atomically finds all `campaign_leads` where `state == 'WAITING'` and `next_action_at <= utcnow()` and the parent `campaign.status == 'RUNNING'`.
  - Uses `SELECT ... FOR UPDATE SKIP LOCKED` to prevent duplicate claiming across multiple worker replicas.
  - Dispatches `send_campaign_email_task.delay(campaign_lead_id)`.

#### 5. Campaign Control Endpoints
- `POST /api/v1/campaigns`: Create campaign with sequence steps.
- `POST /api/v1/campaigns/{id}/launch`: Transition campaign from `REVIEW` to `RUNNING`. Enrolls filtered leads.
- `POST /api/v1/campaigns/{id}/pause`: Instantly pauses campaign. Background workers re-check status and abort active executions.
- `POST /api/v1/campaigns/{id}/resume`: Resumes campaign execution.

#### 6. Verification & Automated Tests
- Test valid and invalid state transitions (e.g. verify `SENT -> REPLIED` is allowed, but `UNSUBSCRIBED -> READY` raises `InvalidStateTransitionError`).
- Test business hour calculation: Ensure an email scheduled on Friday at 4:30 PM with a 2-day delay lands on Tuesday at 9:XX AM local time, NOT on Sunday.
```

---

# Milestone 6: Model Gateway, Bounded Context Assembly & Outbound AI Personalization

### 1. Milestone Scope & Objective
Build the AI Model Gateway and outbound email generation pipeline. Assemble a bounded context package (Company Knowledge + Lead Context + Campaign Objective + Previous Thread), invoke the LLM with strict JSON Schema output contracts, and run hallucination and claim verification filters before approving drafts.

### 2. Detailed Technical Specifications & Deliverables
* **Model Gateway (`packages/ai/gateway.py`):**
  * Centralized interface for LLM calls (Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o).
  * Built-in fallback: If primary provider experiences 5xx or latency timeout (>15s), automatically fall back to secondary model.
  * Telemetry logging: Prompt version, tokens used, latency in ms, cost in USD.
* **Bounded Context Assembly:**
  * DO NOT dump entire knowledge base into the prompt.
  * Retrieve 2–3 high-scoring vector chunks from `knowledge_chunks` using lead company & industry keywords.
  * Inject verified Business Profile, lead details, sequence step instructions, and claims policy.
* **Structured Output Contract (Pydantic Schema):**
  * `subject`: str
  * `body`: str (concise, plain text or lightweight HTML)
  * `personalization_facts`: list[str]
  * `cta`: str
  * `claims_used`: list[str]
  * `confidence`: float (0.0 to 1.0)
  * `risk_flags`: list[str]
  * `recommended_action`: `SEND` or `HUMAN_REVIEW`
* **Safety & Claim Verification:**
  * Validate that any factual claim or metric matches an extracted chunk in the knowledge base.
  * Check against prohibited claims in `BusinessProfile.claims_policy`.

### 3. Edge Cases & Critical Safeguards
* Hallucination Gate: If `confidence < 0.85` or `risk_flags` contains unsupported claims, mark the email for `HUMAN_REVIEW` instead of auto-sending.
* No Fake Research: Never generate sentences like "I saw your recent LinkedIn post" unless that exact post URL and text are present in `lead_enrichment`.

---

### 🟢 Master Production Execution Prompt: Milestone 6

```markdown
### PROMPT: MILESTONE 6 - MODEL GATEWAY, CONTEXT ASSEMBLY & OUTBOUND AI PERSONALIZATION

You are a 12+ Year Veteran AI Systems Architect and Prompt Engineer. Your objective is to build Milestone 6 of the Codenter AI SDR Platform according to Section 7 and Section 15 of the Product Specification.

#### 1. Model Gateway Architecture
In `packages/ai/gateway.py`:
- Create `ModelGateway` class supporting multiple providers (OpenAI, Anthropic):
  ```python
  class ModelGateway:
      async def generate_structured(
          self,
          system_prompt: str,
          user_prompt: str,
          schema: type[BaseModel],
          model: str = "claude-3-5-sonnet-20241022",
          fallback_model: str = "gpt-4o",
          timeout_seconds: float = 15.0,
      ) -> tuple[BaseModel, ModelUsageTelemetry]: ...
  ```
- Automatically log each invocation to `usage_events` table (recording prompt tokens, completion tokens, latency, cost estimate, and workspace_id).
- Handle rate-limit errors and timeouts with immediate fallback to secondary model.

#### 2. Bounded Context Assembly Engine
In `packages/ai/context_builder.py`:
- Implement `assemble_outbound_context(lead: CRMLead, campaign: Campaign, step: CampaignStep, profile: BusinessProfile, db_session) -> dict`:
  1. Retrieve top 3 relevant knowledge chunks using vector cosine similarity search on `pgvector` matching lead's industry and pain points.
  2. Assemble verified value propositions and approved proof points.
  3. Load approved claims and forbidden claims from `profile.claims_policy`.
  4. Include lead's name, company, title, industry, and previous thread summary if step > 1.
  5. Enforce token budget: Context must never exceed 3,000 tokens.

#### 3. Outbound Email Generation Prompt & Schema
In `packages/ai/prompts/outbound_composer.py`:
- Define system prompt enforcing cold outreach best practices:
  - Keep emails under 125 words.
  - Focus on recipient's business problems rather than bragging about features.
  - Clear single low-friction CTA.
  - Tone adapted to `profile.brand_voice`.
- Enforce strict Pydantic output schema:
  ```python
  class OutboundDraftResponse(BaseModel):
      subject: str = Field(..., max_length=100)
      body: str = Field(...)
      personalization_facts: list[str]
      cta: str
      claims_used: list[str]
      confidence: float = Field(..., ge=0.0, le=1.0)
      risk_flags: list[str]
      recommended_action: Literal["SEND", "HUMAN_REVIEW"]
  ```

#### 4. Claim Validation & Policy Filter
In `packages/ai/guardrails/claim_validator.py`:
- Implement `validate_outbound_draft(draft: OutboundDraftResponse, profile: BusinessProfile) -> ValidationResult`:
  - Check for forbidden keywords and disallowed claims.
  - Verify that every claim in `claims_used` exists in the approved profile facts.
  - If ungrounded metrics or unauthorized pricing are detected, override `recommended_action = "HUMAN_REVIEW"`.

#### 5. REST Endpoints
- `POST /api/v1/campaigns/{id}/preview`: Generates sample personalized emails for 3 representative leads in the campaign audience without sending. Returns full structured breakdown including claims and reasoning.

#### 6. Verification & Automated Tests
- Test Model Gateway fallback by simulating primary model timeout and verifying secondary model returns the validated schema.
- Test policy filter: Pass a generated draft containing a fabricated discount ("50% off this week") and verify the validator flags it and sets `recommended_action = "HUMAN_REVIEW"`.
```

---

# Milestone 7: Inbound Email Ingestion, Intent Taxonomy & Grounded Reply Agent

### 1. Milestone Scope & Objective
Build the autonomous Inbound Email subsystem. Ingest webhook/polling events from mailboxes, match incoming messages to leads and threads, run deterministic unsubscribe checks, classify incoming replies across a 14-intent taxonomy, and either trigger grounded AI auto-replies or route to Human Handoff.

### 2. Detailed Technical Specifications & Deliverables
* **14-Intent Taxonomy (`packages/ai/taxonomy.py`):**
  1. `POSITIVE_INTEREST` -> Move toward meeting booking.
  2. `PRICING` -> Grounded answer from verified pricing, or route to sales.
  3. `PRODUCT_QUESTION` -> Grounded answer from knowledge base chunks.
  4. `OBJECTION` -> Approved objection handling script.
  5. `REQUEST_INFO` -> Provide approved collateral/links.
  6. `NOT_INTERESTED` -> Stop campaign sequence.
  7. `UNSUBSCRIBE` -> **Immediate global suppression** + stop sequence.
  8. `WRONG_PERSON` -> Ask/capture correct referral.
  9. `REFERRAL` -> Capture new contact details and update CRM.
  10. `TIMING` -> Pause and schedule future follow-up.
  11. `MEETING_REQUEST` -> Invoke calendar booking flow.
  12. `HUMAN_REQUEST` -> Stop auto-reply and create human handoff task.
  13. `OUT_OF_SCOPE` -> Safe clarification or handoff.
  14. `AUTO_REPLY` -> Mark as Out-of-Office; do NOT count as sales intent.
* **Deterministic Unsubscribe Detector:**
  * Regex and pattern matching executed **before** calling any LLM.
  * Keywords: "unsubscribe", "remove me", "stop emailing", "opt out", "do not contact".
* **Grounded Reply Generation:**
  * Retrieve factual context to answer product/pricing questions.
  * Auto-send **only** if confidence >= threshold (e.g. 0.85) AND intent is safe. Otherwise, place in Human Review Inbox.

### 3. Edge Cases & Critical Safeguards
* False Negative on Unsubscribe: Critical defect. If there is any ambiguity in opt-out intent, default to immediate suppression.
* Angry / Threatening Prospect: Sequence must halt instantly; alert workspace owner.

---

### 🟢 Master Production Execution Prompt: Milestone 7

```markdown
### PROMPT: MILESTONE 7 - INBOUND EMAIL INGESTION, INTENT TAXONOMY & REPLY AGENT

You are a 12+ Year Veteran AI Conversational Agent Architect. Your goal is to build Milestone 7 of the Codenter AI SDR Platform according to Section 8 of the Product Specification.

#### 1. Inbound Ingestion Pipeline
In `apps/worker/tasks/inbound_email.py`:
- Implement `process_inbound_email_task(provider: str, raw_payload: dict)`:
  1. Extract sender email, subject, body, message ID, references, and timestamp.
  2. Normalize email address and find corresponding `CRMLead` and `EmailThread`.
  3. Deduplicate message using hash of (`provider_message_id`, `body_text`).
  4. Save record to `email_messages` table with `direction = 'INBOUND'`.

#### 2. Deterministic Opt-Out / Unsubscribe Detector
In `packages/compliance/opt_out_detector.py`:
- Implement regex and keyword-based check:
  ```python
  def detect_explicit_opt_out(text: str) -> bool: ...
  ```
- If true:
  1. Add email and domain to `suppression_list` table.
  2. Transition `campaign_leads` state to `UNSUBSCRIBED`.
  3. Create record in `unsubscribe_events`.
  4. Abort further AI reply processing immediately.

#### 3. Inbound Intent Classifier (LLM + Structured Output)
In `packages/ai/classifiers/intent_classifier.py`:
- Build prompt classifying reply into exact 14 intents:
  `POSITIVE_INTEREST`, `PRICING`, `PRODUCT_QUESTION`, `OBJECTION`, `REQUEST_INFO`, `NOT_INTERESTED`, `UNSUBSCRIBE`, `WRONG_PERSON`, `REFERRAL`, `TIMING`, `MEETING_REQUEST`, `HUMAN_REQUEST`, `OUT_OF_SCOPE`, `AUTO_REPLY`.
- Return Pydantic schema:
  ```python
  class ReplyClassification(BaseModel):
      primary_intent: str
      confidence: float
      urgency: Literal["LOW", "MEDIUM", "HIGH"]
      sentiment: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]
      extracted_reasoning: str
      extracted_contact_info: Optional[dict] = None
      suggested_action: Literal["AUTO_REPLY", "BOOK_MEETING", "PAUSE_SEQUENCE", "STOP_SEQUENCE", "HUMAN_HANDOFF"]
  ```

#### 4. Grounded Reply Composer & Safety Gating
In `packages/ai/composers/reply_composer.py`:
- For intents requiring answers (`PRODUCT_QUESTION`, `PRICING`, `OBJECTION`, `REQUEST_INFO`):
  1. Fetch top relevant chunks from `knowledge_chunks` via hybrid vector search.
  2. Draft grounded response answering prospect's question directly.
  3. Auto-send gating rule:
     - IF `classification.confidence >= 0.85` AND `suggested_action == 'AUTO_REPLY'` AND `draft.confidence >= 0.85`:
       Enqueue `send_email_task` with generated response.
     - ELSE:
       Flag thread as `HANDOFF_REQUIRED`, store draft in `ai_responses`, and notify human user in Dashboard Inbox.

#### 5. REST Endpoints for Human-in-the-Loop Inbox
- `GET /api/v1/inbox/threads`: List all conversation threads with intent badges, sentiment, and status filter (`NEEDS_REVIEW`, `AUTO_REPLIED`, `CLOSED`).
- `GET /api/v1/inbox/threads/{id}`: View full message timeline, AI classification reasoning, retrieved source chunks, and pending AI draft.
- `POST /api/v1/inbox/threads/{id}/approve`: Approve pending AI draft and send.
- `POST /api/v1/inbox/threads/{id}/handoff`: Assign conversation to a human sales rep and disable AI auto-replies.

#### 6. Verification & Automated Tests
- Test intent classification with 10 sample reply strings.
- Verify that "Take me off your list" triggers deterministic suppression before any AI reply generation.
- Verify that a pricing question when pricing is not in the knowledge base routes to `HUMAN_HANDOFF` instead of hallucinating dollar amounts.
```

---

# Milestone 8: AI Lead Qualification Engine & Bi-Directional CRM Sync-back

### 1. Milestone Scope & Objective
Implement the AI Lead Qualification engine based on the NFAT framework (Need, Fit, Authority, Timing). Extract qualification signals from conversation history, compute structured qualification outputs, and write the qualification status and deal attributes back to the CRM in near real time.

### 2. Detailed Technical Specifications & Deliverables
* **Qualification Framework (NFAT):**
  * **Need:** Does the prospect have a demonstrated pain point that the product solves?
  * **Fit:** Does the company meet ICP criteria (size, industry, stack)?
  * **Authority:** Is the contact a decision maker, influencer, or end user?
  * **Timing:** Immediate, next quarter, unknown, or no need?
* **Structured Qualification Output Schema:**
  * `qualification_status`: `UNQUALIFIED`, `DEVELOPING`, `QUALIFIED`
  * `fit_score`: 0–100
  * `intent`: `LOW`, `MEDIUM`, `HIGH`
  * `need`: str
  * `timing`: `NOW`, `LATER`, `UNKNOWN`
  * `authority`: `DECISION_MAKER`, `INFLUENCER`, `UNKNOWN`
  * `pain_points`: list[str]
  * `next_action`: `BOOK_MEETING`, `FOLLOW_UP`, `HANDOFF`, `STOP`
  * `reason_codes`: list[str]
* **Bi-Directional CRM Sync-back:**
  * When lead reaches `QUALIFIED`, trigger Celery task to update HubSpot Contact properties (`lifecyclestage = 'marketingqualifiedlead'`, custom property `ai_sdr_qualification_summary`).

### 3. Edge Cases & Critical Safeguards
* Over-qualification: Do not mark a lead as `QUALIFIED` solely because they sent a polite email; explicit need or meeting intent is mandatory.
* CRM Sync Failures: If CRM API fails, queue sync task with exponential backoff; never drop qualification data locally.

---

### 🟢 Master Production Execution Prompt: Milestone 8

```markdown
### PROMPT: MILESTONE 8 - AI LEAD QUALIFICATION & CRM SYNC-BACK

You are a 12+ Year Veteran Sales Technology and AI Engineer. Your objective is to build Milestone 8 of the Codenter AI SDR Platform matching Section 9 and Section 5.1 of the Product Specification.

#### 1. AI Qualification Agent
In `packages/ai/agents/qualification_agent.py`:
- Implement `evaluate_lead_qualification(thread: EmailThread, lead: CRMLead, profile: BusinessProfile) -> QualificationResult`:
  - Provide full conversation history (both inbound and outbound messages).
  - Evaluate against the NFAT framework (Need, Fit, Authority, Timing).
  - Enforce Pydantic schema:
    ```python
    class QualificationResult(BaseModel):
        qualification_status: Literal["UNQUALIFIED", "DEVELOPING", "QUALIFIED"]
        fit_score: int = Field(..., ge=0, le=100)
        intent: Literal["LOW", "MEDIUM", "HIGH"]
        need: str
        timing: Literal["NOW", "LATER", "UNKNOWN"]
        authority: Literal["DECISION_MAKER", "INFLUENCER", "UNKNOWN"]
        pain_points: list[str]
        next_action: Literal["BOOK_MEETING", "FOLLOW_UP", "HANDOFF", "STOP"]
        reason_codes: list[str]
    ```

#### 2. Database Persistence
In `packages/common/models/crm.py`:
- Update `CRMLead` record with qualification fields:
  - `qualification_status = result.qualification_status`
  - `qualification_details = result.model_dump()`
  - `is_qualified = True` (if status == 'QUALIFIED')

#### 3. Bi-Directional CRM Sync Worker
In `apps/worker/tasks/crm_sync.py`:
- Implement `sync_lead_outcome_to_crm_task(lead_id: UUID)`:
  1. Load lead, active CRM connection, and field mappings.
  2. Construct CRM vendor payload (e.g. for HubSpot: update `hs_lead_status`, `lifecyclestage`, and custom note with qualification reasons).
  3. Invoke `crm_provider.update_contact(connection.access_token, lead.crm_record_id, payload)`.
  4. Log sync success or error to `audit_logs`.

#### 4. Verification & Automated Tests
- Unit test qualification agent with 3 simulated conversation threads:
  a. Thread A: "We need this urgently for our 50-person sales team, are you available Thursday?" -> Must yield `QUALIFIED`, `timing = NOW`, `next_action = BOOK_MEETING`.
  b. Thread B: "Sounds cool, maybe next year" -> Must yield `DEVELOPING`, `timing = LATER`.
  c. Thread C: "I am an intern, not interested" -> Must yield `UNQUALIFIED`.
- Integration test CRM sync worker verifying correct payload dispatch and error retry on simulated 500 error.
```

---

# Milestone 9: Calendar Engine, Timezone Resolver & Concurrency-Safe Booking

### 1. Milestone Scope & Objective
Implement the autonomous meeting booking engine. Build adapters for Google Calendar and Microsoft Outlook Calendar. Parse prospect meeting availability requests, resolve host free/busy availability in the prospect's timezone, propose 2–3 low-friction slots, and execute double-booking-safe meeting confirmations.

### 2. Detailed Technical Specifications & Deliverables
* **Calendar Provider Abstraction (`packages/calendar/base.py`):**
  * `get_free_busy(start_time, end_time, buffer_minutes)`
  * `create_meeting_event(host_email, attendee_email, title, description, start_time, end_time, idempotency_key)`
  * `cancel_meeting_event(event_id)`
* **Availability Rules & Buffer Engine:**
  * Working hours (e.g. Mon-Fri, 9:00 AM to 5:00 PM host local time).
  * Meeting duration (default 15 or 30 minutes).
  * Buffer time (minimum 15 minutes between back-to-back meetings).
  * Max future booking window (e.g. within next 10 business days).
* **Database Models:**
  * `calendar_connections` (`id`, `workspace_id`, `provider`: `GOOGLE` / `MICROSOFT`, `encrypted_credentials`, `calendar_id`, `settings_json`, `created_at`)
  * `appointments` (`id`, `workspace_id`, `lead_id`, `calendar_connection_id`, `provider_event_id`, `meeting_title`, `start_time`, `end_time`, `status`: `CONFIRMED`, `CANCELLED`, `RESCHEDULED`, `created_at`)

### 3. Edge Cases & Critical Safeguards
* Concurrency / Race Condition: If two prospects select the same slot simultaneously, use an atomic database/provider verification step. The second prospect receives a polite notification offering alternate open slots.
* Sequence Stop Rule: The moment an appointment is confirmed, the campaign sequence for this lead **must stop immediately** (`state = 'MEETING_BOOKED'`).

---

### 🟢 Master Production Execution Prompt: Milestone 9

```markdown
### PROMPT: MILESTONE 9 - CALENDAR ENGINE & CONCURRENCY-SAFE BOOKING

You are a 12+ Year Veteran Scheduling and Protocol Architect. Your objective is to build Milestone 9 of the Codenter AI SDR Platform according to Section 10 of the Product Specification.

#### 1. Calendar Provider Adapters
In `packages/calendar/`:
- Create `base.py` with abstract class `CalendarProvider`:
  ```python
  class CalendarProvider(ABC):
      @abstractmethod
      async def get_availability(self, credentials: dict, start_date: datetime, end_date: datetime, duration_minutes: int) -> list[TimeSlot]: ...
      @abstractmethod
      async def book_event(self, credentials: dict, booking_request: BookingRequest) -> BookingConfirmation: ...
  ```
- Implement `packages/calendar/adapters/google_calendar_adapter.py`: Uses Google Calendar API v3 (`freeBusy.query` and `events.insert`).
- Implement `packages/calendar/adapters/ms_calendar_adapter.py`: Uses Microsoft Graph API (`/me/calendar/getSchedule` and `/me/events`).

#### 2. Slot Calculation & Timezone Conversion Engine
In `packages/calendar/slot_finder.py`:
- Implement `find_prospect_slots(host_availability: list[TimeSlot], prospect_timezone: str, meeting_duration_mins: int = 15, num_slots: int = 3) -> list[str]`:
  - Convert available host slots into formatted strings in prospect's local timezone (e.g. "Thursday, Oct 12 at 2:00 PM EDT").
  - Enforce minimum 24-hour advance notice (never offer slots within the next 24 hours).
  - Enforce 15-minute buffers before and after existing calendar appointments.

#### 3. Concurrency-Safe Booking Pipeline
In `apps/worker/tasks/calendar_tasks.py`:
- Implement `execute_calendar_booking_task(lead_id: UUID, selected_slot: datetime)`:
  1. Acquire Redis lock `booking_lock:{host_calendar_id}:{selected_slot_timestamp}`.
  2. Re-verify host free/busy availability in real time to prevent race conditions.
  3. If slot is taken, trigger `propose_alternate_slots_task(lead_id)` and release lock.
  4. Call `calendar_provider.book_event()` with unique idempotency key.
  5. Store record in `appointments` table.
  6. Transition `campaign_leads` state to `MEETING_BOOKED`.
  7. Enqueue `sync_lead_outcome_to_crm_task` to update CRM deal stage.
  8. Send calendar invite and confirmation email to prospect.
  9. Release lock.

#### 4. REST Endpoints
- `POST /api/v1/integrations/calendar/{provider}/connect`: OAuth connection for Google / Microsoft Calendar.
- `POST /api/v1/calendar/availability`: Query host availability.
- `POST /api/v1/calendar/book`: Manually or programmatically confirm a booking slot.

#### 5. Verification & Automated Tests
- Test slot generator with conflicting busy intervals: Ensure generated slots do not overlap busy intervals and respect buffers.
- Test race condition: Simulate two parallel booking requests for the exact same slot. Verify that exactly ONE succeeds and the second returns a collision error.
```

---

# Milestone 10: Telemetry, Token Metering, Audit Logging & Analytics Funnel

### 1. Milestone Scope & Objective
Implement the comprehensive observability, telemetry, usage metering, and funnel analytics subsystem. Track every state transition, email event, token expenditure, and AI decision with source provenance. Compute real-time analytics for the sales funnel.

### 2. Detailed Technical Specifications & Deliverables
* **5 Core Questions Audit Trail:**
  Every automated SDR action must record:
  1. What happened?
  2. Which rule allowed it?
  3. Which AI model & prompt version was used?
  4. What knowledge chunks/data were retrieved?
  5. What downstream state changed?
* **Sales Analytics Funnel Engine:**
  $$\text{Eligible Leads} \rightarrow \text{Sends} \rightarrow \text{Delivered} \rightarrow \text{Replies} \rightarrow \text{Positive Replies} \rightarrow \text{Qualified} \rightarrow \text{Meetings Booked}$$
* **Usage & Metering Engine:**
  * Aggregate token usage per model provider.
  * Track email send volumes against mailbox and workspace quotas.
  * Calculate estimated dollar cost per generated conversation and meeting.

### 3. Edge Cases & Critical Safeguards
* Performance: High-volume logging must not block transactional API endpoints. Write usage events and audit logs asynchronously or in batched writes.
* Retention: Partition `audit_logs` and `conversation_events` by month for long-term scalability.

---

### 🟢 Master Production Execution Prompt: Milestone 10

```markdown
### PROMPT: MILESTONE 10 - TELEMETRY, TOKEN METERING & ANALYTICS FUNNEL

You are a 12+ Year Veteran Big Data and Observability Architect. Your objective is to build Milestone 10 of the Codenter AI SDR Platform matching Section 19, Section 27, and Section 12 of the Product Specification.

#### 1. Event Models & Audit Schema
In `packages/common/models/telemetry.py`:
- Implement `ConversationEvent`:
  - `id`: UUID (PK), `workspace_id`: UUID (FK), `thread_id`: UUID (FK)
  - `event_type`: ENUM (`EMAIL_SENT`, `INBOUND_RECEIVED`, `INTENT_CLASSIFIED`, `REPLY_GENERATED`, `HANDOFF_TRIGGERED`, `LEAD_QUALIFIED`, `MEETING_BOOKED`, `OPT_OUT_DETECTED`)
  - `rule_name`: VARCHAR, `model_version`: VARCHAR, `prompt_version`: VARCHAR
  - `data_payload`: JSONB, `created_at`: TIMESTAMPTZ (indexed)
- Ensure all automated actions emit a structured `ConversationEvent`.

#### 2. Usage & Token Metering Service
In `packages/ai/metering.py`:
- Implement `record_usage(workspace_id: UUID, event_type: str, units: int, model: str)`:
  - Calculate estimated cost in USD based on model pricing table.
  - Persist to `usage_events` table.
  - Check against workspace spending limits. If spending cap exceeded, pause active campaigns and alert admin.

#### 3. Real-Time Sales Funnel Aggregator
In `packages/analytics/funnel.py`:
- Implement `get_workspace_funnel(workspace_id: UUID, date_from: datetime, date_to: datetime) -> FunnelReport`:
  - Compute Total Enrolled Leads, Sends, Delivery Rate, Bounce Rate, Reply Rate, Positive Reply Rate, Qualified Leads, Meetings Booked, Unsubscribe Rate, Average AI Latency, and Human Handoff Rate.

#### 4. REST Endpoints
- `GET /api/v1/analytics/overview`: Workspace-wide high-level dashboard metrics.
- `GET /api/v1/campaigns/{id}/analytics`: Campaign-specific funnel and conversion metrics.
- `GET /api/v1/usage/summary`: Token expenditure, email count, and billable cost breakdown.

#### 5. Verification & Automated Tests
- Unit test funnel aggregator with synthetic event sequence (100 enrolled -> 95 sent -> 20 replied -> 5 positive -> 2 booked).
- Test token cost calculation accuracy against pricing matrix.
```

---

# Milestone 11: Frontend Web Application (React, Vite, Tailwind, Frosted Glass & Reusable Squircles)

### 1. Milestone Scope & Objective
Construct the responsive, high-performance web dashboard in React 18, Vite, and Tailwind CSS. Implement the **Atomic Reusable Component Library**, the **Ultra-Clean White + 3D Frosted Acrylic Glassmorphism** design language, the **Dynamic Secondary Accent Theme Engine** (defaulting to Cobalt Blue Drafting Engine), and the **Apple Squircle Geometry** applied to all buttons, cards, dialogs, inputs, and badges. Build the 9 core navigation areas: Dashboard Overview, Leads, Campaigns (Builder & Preview), Inbox (Human-in-the-Loop review), Knowledge Base (Website Profile review), Integrations, Calendar, Analytics, and Settings.

### 2. Detailed Technical Specifications & Deliverables
* **Atomic Reusable UI Components (`apps/web/src/components/ui/`):**
  * `SquircleButton.tsx`: Reusable button supporting 5 variants (`primary`, `frosted`, `outline`, `ghost`, `danger`), specular top-edge border highlight, dynamic accent background/ring, smooth continuous squircle curvature.
  * `FrostedGlassCard.tsx`: 3D frosted acrylic container (`bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)]`), specular inner reflection.
  * `SquircleInput.tsx` / `SquircleTextarea.tsx`: Translucent white input field with dynamic accent focus glow.
  * `IntentBadge.tsx`: Frosted acrylic badge with colored indicator dot for the 14 intents.
  * `SquircleModal.tsx`: Floating 3D acrylic dialog with backdrop blur and spring transitions.
  * `ICPScoreGauge.tsx`: Radial/circular 0-100 meter with Hot/Warm/Cold color indicators.
  * `SplitPaneInbox.tsx`: Split-pane conversation browser with thread list and timeline.
  * `ThemePicker.tsx`: Dynamic secondary accent selector with real-time CSS variable updates.
* **Component Architecture:**
  * `apps/web/src/pages/Dashboard`: 8 KPI cards, active campaigns comparison table, real-time funnel bar.
  * `apps/web/src/pages/Campaigns/Builder`: 5-step wizard with live AI email preview on real leads.
  * `apps/web/src/pages/Inbox`: Human-in-the-Loop review pane showing intent badges, AI confidence, knowledge citations, and approval/edit controls.
  * `apps/web/src/pages/Knowledge`: Business profile review card grid with inline edit controls.
  * `apps/web/src/pages/Leads`: Searchable, filterable lead table with ICP score explanation drawers.
* **Sanitization & Security:**
  * All inbound email HTML rendered in the inbox must pass through `DOMPurify.sanitize()`.

### 3. Edge Cases & Critical Safeguards
* Dynamic Theme Persistence: User's secondary accent selection stored in `localStorage` and synced to workspace settings.
* Rendering Safety: Never execute scripts or unsafe links inside inbound email threads.

---

### 🟢 Master Production Execution Prompt: Milestone 11

```markdown
### PROMPT: MILESTONE 11 - FRONTEND WEB APPLICATION (REACT, VITE, FROSTED ACRYLIC & SQUIRCLE UI)

You are a 12+ Year Veteran Principal Frontend Architect & Design Systems Engineer. Your objective is to build Milestone 11 of the Codenter AI SDR Platform strictly following Section 17 of the Product Specification, adhering to the Ultra-Clean White canvas, 3D Frosted Acrylic Glassmorphism, Dynamic Secondary Accent Engine (Cobalt Blue default), and Apple Squircle Geometry.

#### 1. Setup, Tailwind Config & Theme System
In `apps/web/`:
- Initialize React 18 + TypeScript + Vite + Tailwind CSS.
- Install Lucide React, TanStack React Query, Axios, React Router v6, DOMPurify, clsx, tailwind-merge.
- Configure `tailwind.config.js`:
  - Register custom box-shadows: `glass: 'var(--shadow-glass)'`, `glass-elevated: 'var(--shadow-glass-elevated)'`.
  - Register backdrop blurs: `backdrop-blur-xl: '20px'`.
  - Register squircle continuous curvature border radii: `squircle-sm: '12px'`, `squircle-md: '18px'`, `squircle-lg: '24px'`, `squircle-xl: '32px'`.
- Implement `apps/web/src/index.css` with CSS custom properties for canvas base, specular reflections, and the dynamic secondary accent engine (`--accent-primary: #1D4ED8;` Cobalt Blue default).
- Implement `apps/web/src/context/ThemeContext.tsx`:
  - Provides `accentColor` state (`cobalt`, `indigo`, `emerald`, `violet`, `amber`).
  - Sets `data-accent` on root document element and persists selection in `localStorage`.

#### 2. Atomic Reusable Component Library (`apps/web/src/components/ui/`)
1. `SquircleButton.tsx`:
   - Props: `variant` ('primary' | 'frosted' | 'outline' | 'ghost' | 'danger'), `size` ('sm' | 'md' | 'lg'), `isLoading`, `children`.
   - Styles: Continuous squircle `rounded-[18px]`, specular top highlight `shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.4)]`, dynamic accent background on primary (`bg-[var(--accent-primary)] hover:bg-[var(--accent-hover)] text-white`), active spring scale `active:scale-[0.98]`.
2. `FrostedGlassCard.tsx`:
   - 3D frosted acrylic container: `bg-white/75 backdrop-blur-xl border border-white/80 shadow-[var(--shadow-glass)] rounded-[24px] p-6`.
   - Top inner specular highlight: `shadow-[inset_0_1px_1px_0_rgba(255,255,255,0.95)]`.
3. `SquircleInput.tsx` & `SquircleTextarea.tsx`:
   - Translucent surface: `bg-white/70 backdrop-blur-md border border-slate-200/80 rounded-[16px] px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[var(--accent-primary)] focus:ring-4 focus:ring-[var(--accent-glow)] transition-all`.
4. `IntentBadge.tsx`:
   - Frosted pill: `rounded-[12px] px-2.5 py-1 text-xs font-semibold backdrop-blur-md border border-white/60 flex items-center gap-1.5`.
   - 14 Intent variants with distinct glowing status dots (e.g. `POSITIVE_INTEREST`: emerald glow, `PRICING`: amber glow, `UNSUBSCRIBE`: rose glow, `QUESTION`: cobalt/accent glow).
5. `SquircleModal.tsx`:
   - Floating dialog: `fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-md`.
   - Content: `bg-white/90 backdrop-blur-2xl rounded-[32px] border border-white shadow-2xl p-6 max-w-lg w-full`.
6. `ICPScoreGauge.tsx`:
   - Visual circular indicator for 0–100 ICP fit score with dynamic accent ring, score badge (Hot/Warm/Cold), and popup breakdown of positive/negative scoring reasons.
7. `ThemePicker.tsx`:
   - Visual swatch selector allowing the user to switch the secondary accent between Cobalt Blue, Electric Indigo, Emerald Precision, Cyber Violet, and Sunset Amber.

#### 3. Core Pages Implementation
- `DashboardPage` (`/`):
  - 8 KPI Frosted Acrylic Cards: Emails Sent, Delivery Rate, Replies, Positive Replies, Qualified Leads, Meetings Booked, Unsubscribes, AI Handoffs.
  - Active campaigns comparison table with squircle status badges.
  - Conversion funnel bar.
- `CampaignBuilderWizard` (`/campaigns/new`):
  - 5-step wizard: 1. Audience Filters -> 2. Objective & Tone -> 3. Sequence Steps -> 4. AI Policy -> 5. Live Preview.
  - In Step 5, display live generated personalized emails for sample leads with claims and confidence badges.
- `InboxPage` (`/inbox`):
  - SplitPane dual-pane layout:
    - Left Pane: Scrollable thread list with sender name, company, time, snippet, and colored `IntentBadge`.
    - Right Pane: Full thread conversation timeline. Shows AI classification pill, reasoning breakdown, grounded knowledge citations with source URLs, and pending draft.
    - Action Bar: `SquircleButton` for "Approve & Send", "Edit Draft", "Assign to Human", and "Suppress Lead".
- `KnowledgePage` (`/knowledge`):
  - Card grid displaying extracted facts: Company Summary, Offerings, Value Props, FAQs, Pricing, and Claims Policy.
  - Each item displays source URL link and confidence score with inline edit modal.
- `LeadDetailPage` (`/leads/:id`):
  - Lead contact information, `ICPScoreGauge` with detailed reason breakdown, campaign step status, and manual override controls (`Pause`, `Resume`, `Suppress`).

#### 4. HTML Email Sanitization
- In `ThreadTimeline.tsx`:
  - Render inbound HTML email bodies strictly through `DOMPurify.sanitize(email.body_html, { USE_PROFILES: { html: true } })`.

#### 5. Verification & Tests
- Vitest unit tests:
  a. Verify `SquircleButton` renders with correct variant classes and squircle curvature.
  b. Verify `ThemePicker` updates the `data-accent` attribute on root.
  c. Verify `IntentBadge` maps all 14 intents to correct visual styles.
  d. Verify `DOMPurify` strips script tags from malicious inbound email fixture.
```

---

# Milestone 12: AI Benchmark Evals, End-to-End Test Suite, Hardening & Voice Handoff

### 1. Milestone Scope & Objective
Conduct rigorous platform hardening, AI evaluation regression testing, end-to-end integration testing across all failure modes, Dockerized multi-worker orchestration, and implement the Interpulse AI voice agent handoff interface.

### 2. Detailed Technical Specifications & Deliverables
* **AI Evaluation Harness (`tests/ai_eval/`):**
  * Fixed benchmark dataset of 50 labeled inbound replies.
  * Metrics: Intent classification accuracy ($\ge 95\%$), Grounded answer accuracy ($\ge 98\%$), Hallucinated claim rate ($= 0\%$).
  * **Unsubscribe Recall Requirement:** $100.0\%$ (Zero false negatives permitted).
* **Failure Handling Matrix Verification (12 Scenarios):**
  * Website unavailable -> Mark scan failed; do not fabricate profile.
  * Pages blocked -> Continue with accessible pages; show coverage.
  * CRM token expired -> Pause sync; notify user; do not silently drop records.
  * Mailbox auth fails -> Disable sending; require reconnection.
  * Provider rate limit (429) -> Exponential backoff and retry.
  * Hard bounce -> Suppress recipient and stop sequence immediately.
  * Duplicate webhook -> Discard duplicate event via event ID hash.
  * AI provider down -> Trigger fallback model; queue if offline.
  * Low AI confidence -> Route to human review task.
  * Calendar slot race condition -> Re-check availability and offer alternatives.
  * DB/queue outage -> Do not send from stale in-memory state.
  * Campaign paused mid-flight -> Worker aborts send before dispatch.
* **Interpulse Voice Handoff Interface:**
  * Abstract interface to trigger an outbound conversational voice agent call (via Interpulse) when a qualified prospect requests a phone conversation.
* **Production Docker Topology:**
  * Multi-stage Dockerfile for FastAPI backend.
  * Multi-stage Dockerfile for Celery workers (separated into `worker-crawler` with Playwright dependencies and `worker-email` lightweight).
  * Production Docker Compose with health checks and Nginx reverse proxy.

### 3. Edge Cases & Critical Safeguards
* Zero-Tolerance Unsubscribe Failure: The automated test suite must fail the CI/CD pipeline if even a single unsubscribe variation is missed.
* Graceful Shutdown: Celery workers must handle `SIGTERM` cleanly, completing in-flight sends before terminating.

---

### 🟢 Master Production Execution Prompt: Milestone 12

```markdown
### PROMPT: MILESTONE 12 - HARVESTING, AI EVALS, E2E TESTS & PRODUCTION DEPLOYMENT

You are a 12+ Year Veteran Principal DevOps and AI Quality Assurance Architect. Your objective is to build Milestone 12 of the Codenter AI SDR Platform according to Section 20, Section 21, Section 24, and Section 26 of the Product Specification.

#### 1. AI Benchmark Evaluation Suite
In `tests/ai_eval/`:
- Create `benchmark_dataset.json` containing 50 labeled edge-case emails covering all 14 intents.
- Implement `run_ai_evals.py`:
  - Measure primary intent classification precision and recall.
  - Measure unsubscribe detection recall. CRITICAL: Assert `unsubscribe_recall == 1.0`. Any missed unsubscribe must fail the build.
  - Measure hallucination rate on grounded FAQ and pricing answers. Assert `hallucination_rate == 0.0`.
  - Output automated evaluation report in Markdown and JSON.

#### 2. End-to-End System Scenarios (Playwright / Pytest)
In `tests/e2e/`:
- Implement test suite verifying the 9 Golden Path scenarios:
  1. Complete onboarding flow: URL input -> Web scan -> Review profile.
  2. CRM import -> Deduplication -> Lead scoring.
  3. Campaign creation -> Schedule window -> Send execution.
  4. Positive reply -> AI classification -> Grounded response -> Calendar slot selection -> Meeting booked -> Sequence auto-stopped.
  5. Unsubscribe reply -> Instant suppression -> Verification that future sequence steps are canceled.
  6. Ambiguous/out-of-scope question -> Safe routing to Human Handoff.
  7. Simulated provider 429 rate limit -> Exponential retry backoff.
  8. Duplicate webhook ingestion -> Verification of exact single state change.
  9. Campaign pause action -> Active background jobs check database and abort before sending.

#### 3. Interpulse AI Voice Handoff Subsystem
In `packages/ai/voice_handoff.py`:
- Implement `InterpulseHandoffService`:
  - When lead is qualified and indicates phone/voice preference:
    `handoff_to_interpulse(lead: CRMLead, conversation_summary: str, scheduled_call_time: Optional[datetime])`
  - Dispatches signed webhook payload to Codenter Interpulse voice agent platform.
  - Logs handoff event in `conversation_events` and CRM.

#### 4. Production Containerization & Deployment Topology
In `infra/docker/`:
- Multi-stage `Dockerfile.api`: Python 3.11 slim, non-root user, Uvicorn production settings.
- Multi-stage `Dockerfile.worker`: Python 3.11 slim with Celery.
- Multi-stage `Dockerfile.crawler`: Includes Playwright Chromium headless dependencies.
- `docker-compose.prod.yml`:
  - `nginx`: Reverse proxy with SSL termination and rate limiting.
  - `web`: Nginx serving static Vite React build.
  - `api`: FastAPI application (scaled to 3 replicas).
  - `worker-email`: Celery workers processing email and scheduler queues.
  - `worker-crawler`: Celery workers processing website crawls.
  - `worker-ai`: Celery workers processing LLM classifications and RAG tasks.
  - `celery-beat`: Dedicated scheduler daemon.
  - `postgres`: PostgreSQL 16 with pgvector extension.
  - `redis`: Redis 7 with AOF persistence.
- Healthcheck scripts for all containers (`/healthz`).

#### 5. Verification & Acceptance
- Execute complete automated test runner: `pytest tests/unit tests/integration tests/e2e tests/ai_eval`.
- Ensure all 18 MVP Acceptance Criteria in Section 25 of the Product Specification pass with 100% compliance.
```

---

## Developer Execution Strategy & Next Steps

1. **Sequential Execution:** Always complete and verify each milestone before moving to the next.
2. **Deterministic Rules Over LLMs:** Always enforce deterministic code checks for opt-outs, business hours, and mailbox caps.
3. **Continuous Grounding:** Never bypass the RAG retrieval layer or Model Gateway.
4. **Idempotency Everywhere:** Ensure every webhook, background task, and API mutation is safe to retry.
5. **Aesthetic Consistency:** Every new frontend component must inherit the `FrostedGlassCard` or `SquircleButton` base, continuous squircle geometry (`rounded-squircle`), and dynamic secondary accent variable bindings.
