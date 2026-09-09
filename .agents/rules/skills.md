---
trigger: always_on
description: Core architectural rules, deterministic safety, security, and frontend design system for Codenter AI SDR.
---

# CODENTER AI SDR PLATFORM — CORE ENGINEERING & ARCHITECTURAL RULES
### Enforced by 12+ Year Veteran Principal AI Systems & Full-Stack Architect
**Authority:** Derived strictly from `Codenter_AI_SDR_Developer_Product_Specification.docx` (v1.0, Sep 2026) and `Codenter_AI_SDR_Implementation_Milestones_and_Prompts.md`. Mandatory across all frontend, backend, AI, DB, and ops tasks.

---

## 1. Core Engineering Philosophy & Deterministic Safety

1. **Deterministic Rules > AI Guesswork:**
   - Inbound opt-out phrases ("unsubscribe", "stop", "remove me", "do not contact") MUST be intercepted by **deterministic regex before calling any LLM** to suppress the lead immediately.
   - Mailbox daily caps, business-hour windows, pacing jitter, and stop rules are hard-coded constraints that no AI output can override.

2. **Zero Hallucination & Strict Grounding:**
   - Never invent pricing, discounts, SLAs, features, or availability.
   - If an inquiry cannot be verified against active `BusinessProfile` or retrieved `knowledge_chunks`, set `requires_human_review: true` or route to human sales handoff.
   - Every knowledge chunk must retain its `source_url` and `extraction_timestamp`.

3. **Database as Single Source of Truth:**
   - PostgreSQL is the only state store; Redis and Celery are execution mechanisms, NOT state stores.
   - All state transitions (`CampaignState`, `LeadSequenceState`) must be atomically committed in DB before external side-effects.
   - Workers must re-verify DB state before dispatch (e.g. abort send if campaign paused mid-flight).

4. **9 Absolute Stop Conditions:** Sequences halt instantly and irreversibly upon:
   1. Explicit unsubscribe / opt-out signal.
   2. Hard bounce or provider suppression.
   3. Inbound reply received (if configured).
   4. Meeting confirmed on calendar.
   5. Lead manually paused or suppressed by user.
   6. CRM indicates active sales deal/opportunity.
   7. Human handoff requested or low AI confidence.
   8. Maximum sequence steps reached.
   9. Workspace billing or compliance block.

---

## 2. Multi-Tenant Isolation, Security & Privacy

1. **Tenant Boundaries:** Every business DB query MUST enforce `workspace_id == current_workspace.id`. Never trust client-supplied `workspace_id` from request bodies or URL params; derive tenant identity strictly from authenticated JWT claims via `get_current_workspace_context`. Celery jobs must explicitly carry and deserialize `workspace_id`.
2. **Credential Encryption at Rest:** OAuth tokens, refresh tokens, and provider secrets must be encrypted at rest using AES-256-GCM envelope encryption. Plaintext tokens must never be logged or persisted. Use 15-min JWTs with encrypted HttpOnly refresh cookies.
3. **Inbound Email Sanitization:** All inbound HTML email rendered in the UI must pass through `DOMPurify.sanitize(htmlContent, { USE_PROFILES: { html: true } })`. Raw `<script>`, `<iframe>`, or inline event handlers are strictly forbidden.
4. **Idempotency & Webhook Security:** Verify cryptographic signatures on all webhooks (Google, Microsoft, HubSpot). Handlers must be idempotent, deduplicating via event ID hashes and Redis distributed locks.

---

## 3. External Integrations & Deliverability Controls

1. **Provider Abstraction:** All CRM, Email, and Calendar integrations must implement common abstract interfaces (`CRMProvider`, `EmailProvider`, `CalendarProvider`). Domain logic must never couple directly to vendor SDKs.
2. **Email Deliverability Safeguards:**
   - Enforce per-mailbox daily caps (30–50 cold emails/day).
   - Anti-spam pacing jitter: Never burst sends. Enforce randomized sleep delays (120s to 300s) between outbound dispatches.
   - Domain health: Verify SPF, DKIM, DMARC. On HTTP 401 auth failure, immediately mark mailbox `REVOKED`, pause outbound queues, and alert user.
   - Double-send protection: Acquire Redis lock on `send_lock:{workspace_id}:{lead_id}` before dispatching.
3. **Calendar Booking Safety:** Never declare a meeting booked until provider returns verified event ID. Use atomic slot locking to eliminate race conditions. Enforce 15-min buffers before/after events and convert all slots to prospect local timezone.

---

## 4. AI Architecture, Model Gateway & Grounding

1. **Model Gateway:** All LLM calls route through `ModelGateway` with full telemetry (model, prompt version, prompt/completion tokens, latency, cost USD, `workspace_id`). Auto-fallback: If primary (Claude 3.5 Sonnet) fails or exceeds 15s timeout, retry immediately with secondary (GPT-4o).
2. **Bounded Context:** Never dump the full knowledge base into prompts. Retrieve top 2–3 pgvector chunks via cosine similarity matching lead industry/pain points. Max prompt context: 3,000 tokens.
3. **Structured Outputs:** The API must never parse free-form model text to determine state. All AI generation, intent classification, and qualification must return validated Pydantic JSON schemas.
4. **14-Intent Taxonomy:** Classify replies strictly into: `POSITIVE_INTEREST`, `PRICING`, `PRODUCT_QUESTION`, `OBJECTION`, `REQUEST_INFO`, `NOT_INTERESTED`, `UNSUBSCRIBE`, `WRONG_PERSON`, `REFERRAL`, `TIMING`, `MEETING_REQUEST`, `HUMAN_REQUEST`, `OUT_OF_SCOPE`, `AUTO_REPLY`. Auto-replies permitted only when `confidence >= 0.85` and intent is safe; otherwise route to Human Inbox.

---

## 5. Frontend Design System: Apple Frosted Acrylic & Squircle Architecture

1. **Visual Foundation:**
   - **Canvas:** Ultra-Clean Pristine White (`#FFFFFF` surface, `#FAFBFC` canvas, `#E2E8F0` borders).
   - **3D Frosted Acrylic Glassmorphism:** Translucent layers (`rgba(255,255,255,0.75-0.88)`), heavy blur (`backdrop-blur-xl: 20px`), specular top reflection (`inset 0 1px 1px 0 rgba(255,255,255,0.95)`), double borders (`border border-white/80`), and diffuse soft drop-shadows.
   - **Dynamic Secondary Accent:** Driven by CSS variables (`--accent-primary`, `--accent-hover`, `--accent-glow`). Defaults to **Cobalt Blue Drafting Engine** (`#1D4ED8` / `#2563EB`). Supports live user switching (`data-accent`: cobalt, indigo, emerald, violet, amber) with `localStorage` persistence.
   - **Continuous Apple Squircle Geometry:** Standard sharp corners are strictly forbidden. All buttons, cards, modals, badges, inputs, and avatars must use continuous curvature squircles (`border-radius: 18px / 24px; corner-smoothing: squircle` / `@squircle` utility).

2. **Core CSS Tokens (`apps/web/src/index.css`):**
```css
:root {
  --bg-canvas: #FAFBFC; --bg-surface: #FFFFFF; --bg-surface-frosted: rgba(255,255,255,0.75);
  --border-glass: rgba(255,255,255,0.80); --border-subtle: #E2E8F0;
  --text-primary: #0F172A; --text-secondary: #475569; --text-muted: #94A3B8;
  --accent-primary: #1D4ED8; --accent-hover: #1E40AF; --accent-subtle: #EFF6FF;
  --accent-glow: rgba(29,78,216,0.22); --accent-border: rgba(29,78,216,0.35);
  --shadow-glass: 0 10px 25px -5px rgba(15,23,42,0.04), 0 8px 10px -6px rgba(15,23,42,0.03);
  --specular-highlight: inset 0 1px 1px 0 rgba(255,255,255,0.95);
  --squircle-sm: 12px; --squircle-md: 18px; --squircle-lg: 24px; --squircle-xl: 32px;
}
[data-accent="indigo"] { --accent-primary: #4F46E5; --accent-hover: #4338CA; --accent-glow: rgba(79,70,229,0.22); }
[data-accent="emerald"] { --accent-primary: #059669; --accent-hover: #047857; --accent-glow: rgba(5,150,105,0.22); }
[data-accent="violet"] { --accent-primary: #7C3AED; --accent-hover: #6D28D9; --accent-glow: rgba(124,58,237,0.22); }
[data-accent="amber"] { --accent-primary: #D97706; --accent-hover: #B45309; --accent-glow: rgba(217,119,6,0.22); }
```

3. **Atomic Reusable Components (`apps/web/src/components/ui/`):**
   - `SquircleButton`: Variants (`primary`, `frosted`, `outline`, `ghost`, `danger`), squircle `rounded-[18px]`, specular highlight, active spring scale `active:scale-[0.98]`.
   - `FrostedGlassCard`: 3D acrylic `bg-white/75 backdrop-blur-xl border border-white/80 rounded-[24px]` with specular reflection.
   - `SquircleInput` / `SquircleTextarea`: Translucent `bg-white/70 backdrop-blur-md rounded-[16px]`, focus glow `ring-4 ring-[var(--accent-glow)]`.
   - `IntentBadge`: Frosted squircle pill `rounded-[12px]` with glowing status dot for all 14 intents.
   - `SquircleModal`: Floating 3D acrylic dialog `bg-white/90 backdrop-blur-2xl rounded-[32px]` with blurred backdrop.
   - `ICPScoreGauge`: Radial 0–100 meter with Hot/Warm/Cold color bands and reason popovers.
   - `SplitPaneInbox`: Resizable dual-pane container (left: thread browser; right: timeline + AI reasoning + citations).
   - `ThemePicker`: Dynamic secondary accent selector.

4. **Mandatory Navigation Views:**
   `Overview` (`/`), `Leads` (`/leads`), `Campaigns` (`/campaigns`), `Inbox` (`/inbox`), `Knowledge` (`/knowledge`), `Integrations` (`/integrations`), `Calendar` (`/calendar`), `Analytics` (`/analytics`), `Settings` (`/settings`).

---

## 6. Distributed Task Scheduling & Concurrency

1. **Timezone Handling:** Schedule timestamps (`next_action_at`) stored in UTC. Business hours (Mon-Fri, 9:00 AM – 5:00 PM) calculated dynamically at execution in recipient's local timezone with randomized jitter (5–45m).
2. **Worker Concurrency:** Atomic task claiming via `SELECT ... FOR UPDATE SKIP LOCKED`. Separate worker queues: isolate heavy Playwright rendering (`worker-crawler`) from email dispatches (`worker-email`) and AI reasoning (`worker-ai`).

---

## 7. Observability, Telemetry & Quality Assurance

1. **5-Question Audit Trail:** Every SDR action emits an immutable `ConversationEvent` recording: 1. *What happened?* 2. *Which rule allowed it?* 3. *Model & prompt version?* 4. *Knowledge chunks used?* 5. *Downstream state changed?*
2. **CI/CD AI Evaluation Gates:**
   - **Unsubscribe Recall:** Assert strictly `100.0%` recall on benchmark dataset (zero false negatives allowed).
   - **Hallucination Rate:** Assert `0.0%` unsupported claims on grounded FAQ and pricing responses.
   - **Intent Accuracy:** Assert >= 95.0% classification accuracy.
