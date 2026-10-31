# Wave 10 monkey round 1, API/MCP (fresh stack on 14753262)

High
- H1 #567 race: 6 parallel creates by 3 curators gave three 201s for one entity (WT1); the unique index includes created_by;
  two duplicates were approved (second without a curation).

Medium
- M1 #558 bypass: enable export_evidence_public with a session while the scope is private, then set is_public true with a token
  or MCP; anonymous export shows evidence immediately.
- M2 KGDB summaries end "Classification could not be determined." because KGDB bands have no description (scoring/clingen.py ~303).
- M3 hotspot flag fires on any curation with only 1-2 scoring variants (100% from 2 variants): noise on small curations.
- M4 #281 /gene-assignments/bulk and single create drop due_date silently (200, null); the schema lacks the field (UI sends a PUT after).

Low
- L1 /score returns no warnings.
- L2 submit accepts "abc" in a number table column and a blank required zygosity (required table column not enforced server side).
- L3 methodology import dry run labels a refused schema "create".
- L4 a read-only token still sees import_methodology in the MCP tool list.
- L5 disease correction: reason length message counts padding ("7 characters, min 3"); audit logs null old values.
- L6 error text and codes: 403 "Not authorized to access this scope" where a role is missing; 4-eyes refusals return 400, not 403/409.
- L7 backup: two runs in the same second share a .partial file, one fails.
- L8 (untested) PubMed/ontology checks at submit accepted fake PMIDs in this stack.

Passes: import authz, versioning, all 422 cases, audit rows; every draft-4 rule, caps, LOD step, section minimum and flags;
susceptibility (entity key, p value and OR rules); export matrix and diagnostics; delete permissions; corrector rules with two
reviewers; due-date round trip, member removal and re-add; backup checks, retention, clean failures.
Not tested: UI, approvals_require_session, review through MCP.
