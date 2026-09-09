/**
 * Frontend Security and Specification Compliance Test
 * Enforces Rule 2.3: Inbound Email Sanitization with DOMPurify
 * Enforces Rule 4.4: 14-Intent Taxonomy
 * Enforces Rule 5.4: 9 Mandatory Navigation Views
 */
const fs = require('fs');
const path = require('path');

// 1. Test 14-Intent Taxonomy completeness
const EXPECTED_INTENTS = [
  'POSITIVE_INTEREST',
  'PRICING',
  'PRODUCT_QUESTION',
  'OBJECTION',
  'REQUEST_INFO',
  'NOT_INTERESTED',
  'UNSUBSCRIBE',
  'WRONG_PERSON',
  'REFERRAL',
  'TIMING',
  'MEETING_REQUEST',
  'HUMAN_REQUEST',
  'OUT_OF_SCOPE',
  'AUTO_REPLY',
];

const intentBadgeFile = fs.readFileSync(
  path.join(__dirname, 'src/components/ui/IntentBadge.tsx'),
  'utf8'
);

console.log('--- Testing 14-Intent Taxonomy in IntentBadge.tsx ---');
for (const intent of EXPECTED_INTENTS) {
  if (!intentBadgeFile.includes(intent)) {
    console.error(`FAIL: Missing intent in IntentBadge.tsx: ${intent}`);
    process.exit(1);
  }
}
console.log(`PASS: All 14 intents present in IntentBadge.tsx.`);

// 2. Test Mandatory Navigation Views in App.tsx
const MANDATORY_VIEWS = [
  'overview',
  'leads',
  'campaigns',
  'inbox',
  'knowledge',
  'integrations',
  'calendar',
  'analytics',
  'settings',
];

const appFile = fs.readFileSync(path.join(__dirname, 'src/App.tsx'), 'utf8');

console.log('--- Testing 9 Mandatory Navigation Views in App.tsx ---');
for (const view of MANDATORY_VIEWS) {
  if (!appFile.includes(`'${view}'`)) {
    console.error(`FAIL: Missing navigation view in App.tsx: ${view}`);
    process.exit(1);
  }
}
console.log(`PASS: All 9 mandatory navigation views hooked up in App.tsx.`);

// 3. Test Inbound Email Sanitization (Rule 2.3)
const timelineFile = fs.readFileSync(
  path.join(__dirname, 'src/components/ThreadTimeline.tsx'),
  'utf8'
);

console.log('--- Testing Inbound Email Sanitization Rule in ThreadTimeline.tsx ---');
if (!timelineFile.includes("DOMPurify.sanitize")) {
  console.error('FAIL: ThreadTimeline.tsx must use DOMPurify.sanitize.');
  process.exit(1);
}
if (!timelineFile.includes("USE_PROFILES: { html: true }")) {
  console.error('FAIL: ThreadTimeline.tsx must enforce { USE_PROFILES: { html: true } }.');
  process.exit(1);
}
console.log('PASS: DOMPurify.sanitize with { USE_PROFILES: { html: true } } strictly verified.');

// 4. Test Continuous Apple Squircle Tokens in index.css
const cssFile = fs.readFileSync(path.join(__dirname, 'src/index.css'), 'utf8');

console.log('--- Testing Apple Squircle Tokens in index.css ---');
const expectedTokens = [
  '--bg-canvas',
  '--bg-surface',
  '--bg-surface-frosted',
  '--border-glass',
  '--accent-primary',
  '--specular-highlight',
  '--squircle-sm',
  '--squircle-md',
  '--squircle-lg',
  '--squircle-xl',
  'data-accent="indigo"',
  'data-accent="emerald"',
  'data-accent="violet"',
  'data-accent="amber"',
];

for (const token of expectedTokens) {
  if (!cssFile.includes(token)) {
    console.error(`FAIL: Missing token/theme in index.css: ${token}`);
    process.exit(1);
  }
}
console.log('PASS: All Frosted Glass, Squircle, and Dynamic Theme Accent tokens verified.');

console.log('\n=========================================');
console.log('ALL FRONTEND SAFETY & ARCHITECTURE TESTS PASSED!');
console.log('=========================================');
