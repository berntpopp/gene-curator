# PR 441 candidate browser gate

Exact candidate c51ad81; fresh isolated monkey stack; actual Chromium UI. Full core lifecycle59/59 pass and narrow25/25 pass, zero fatal errors.

Core: platform/scope admin, curator, reviewer, viewer/pending-member; save/reload; precuration submit/independent approve; curation first-round request changes/revision/resubmit; two independent approvals; active viewer read-only; re-curation prefill/link/save/reload/submit/two approvals; original archived; admin-author cannot approve own work. The former baseline #430 assertion now passes.

Narrow: already-approved reviewer has can_review=true,has_approved=true,remaining1; Approve hidden, Request changes shown and executed in UI; browser-origin authenticated comment+resolve succeeds. Resubmission resets has_approved and remaining2. Legacy API setup assigns three independent reviewers and records two approvals, leaving one review pending; actual state in_review/has_approved=true/remaining0. Already-approved Bob sees enabled Approve and activates through actual UI.

Comment coverage distinction: after own approval the evidence diff is empty, so no visible composer exists; comment permission exercised with browser-origin authenticated API, not claimed as UI composer interaction. No API substitution for primary UI lifecycle transitions. Explicit legacy API setup is the narrow edge under test.

One initial harness fixture mistake tried to reassign an automatically reassigned Bob pending review; preserved failed run at /tmp/w5-pr441-candidate-review-harness-failure.json. Corrected helper reuses existing pending review; repeated narrow flow on UI-created re-curation passed25/25. No product fixes or weakened assertions.

Evidence: /tmp/w5-pr441-candidate-preserved and the core/review result JSON files. IBM Plex font allow fix remains scratch-only; known non-admin /members403 and occasional Vuetify scroll warning remain baseline noise. Clinical scoring/defaults not verified by these minimal derived fixtures.
