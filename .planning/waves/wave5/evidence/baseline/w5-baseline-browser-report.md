# Wave 5 v0.6.0 baseline browser evidence

Reference: a7538d1, fresh Postgres 5455 as app_user; API 8052, Vite 5190. Evidence preserved at /tmp/w5-baseline-preserved.

Completed through actual Chromium UI: pending viewer denied before acceptance, invitation acceptance, scope access; curator precuration save/reload/submit; independent reviewer approval and automatic curation creation; curator curation save/reload/submit, reviewer request changes, feedback display, revision save/reload/resubmit; first and second independent reviewer approvals and active curation; viewer read-only; re-curation prefill, approved-precuration link preservation, save/reload/submit, two independent approvals, original archived and replacement active; admin-authored precuration/case and absence of own approval control. Authenticated API used for fixtures and state read-back; all workflow transitions above were browser clicks. Published original methodologies unchanged; isolated valid derived minimal schemas used.

Known baseline failure retained: #430 already-approved Bob still sees enabled Approve; native c7 JSON records failed assertion. All later independent lifecycle phases passed. Initial harness selector mistakes and response-matcher failures remain in raw events; corrected runner uses aria-pressed for item acceptance.

Additional pre-existing observations (no repairs): accepted seed memberships have NULL accepted_at; newly-created workflow pair cannot set data_mapping through UI/API; one-section derived schema displays no fields because tab handling excludes its only section. Existing excluded #393 causes non-admin /members 403 console noise. Authentic ClinGen precuration save/reload passed; first-click save/submit exploration inconclusive (known #406), no clinical score claim.

Infrastructure limitation: shared-node_modules IBM Plex font URLs denied by Vite fs allow; baseline screenshots use fallback font. Dedicated restricted startup override prepared for fresh merged-PR gates.

Claude Opus 5.5 monthly spend limit stopped the initial browser agent; native Playwright continuation completed approval/re-curation/D1 phases. No fallback model, billing/authentication change, product edit, or issue creation.
