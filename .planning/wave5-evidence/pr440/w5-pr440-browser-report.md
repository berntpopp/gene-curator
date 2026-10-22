# PR 440 fresh browser gate

Commit 4fe8b6d; fresh monkey-stack; API app_user; UI 5190/API 8052/PG 5455.

Full UI lifecycle: 58/59 assertions pass, zero fatal errors. The single failure is unchanged baseline #430: repeat Approve remains enabled after Bob approved. Pending viewer denial/acceptance, curator and administrator authorship, save/reload, first review requesting changes, revised second review with two independent approvals, viewer read-only, admin D1, re-curation prefill/link/save/reload/review/activation and original archival all pass.

PR-specific: 28/28 assertions pass. Two valid derived catalogue fixtures activated through actual precuration and curation UI. First has disease only in linked precuration; second has a different curation-owned disease. Existing case-file UI displays both effective disease names; matrix shows member private scope and active-curation links. Authenticated outsider sees neither private scope nor disease. Browser-origin authenticated legacy catalogue queries/options return inherited disease, respect own-disease precedence, and hide private data for outsider.

Supplementary SQL: real app_user (superuser=false,bypassrls=false) returns two numeric rows (genetic/experimental/total all0.0) matching stored scoring keys; outsider returns0 rows. Numeric zero is intentional minimal fixture, no clinical score-validity claim.

UI coverage limitation: matrix UI has only Agreement/scope filters; no disease-filter control exists. No disease-filter click-flow was claimed. Legacy API filter tested through browser-origin authenticated fetch; no new UI feature added.

Fonts: IBM Plex Sans verified status=loaded in document.fonts; exact dependency-path fs.allow override in scratch startup only. Raw evidence: /tmp/w5-pr440-preserved, /tmp/w5-pr440-core-results.json, /tmp/w5-pr440-catalogue-results.json, /tmp/w5-pr440-sql-view-results.json. Non-admin /members403 and occasional Vuetify scroll warning are unchanged baseline noise.
