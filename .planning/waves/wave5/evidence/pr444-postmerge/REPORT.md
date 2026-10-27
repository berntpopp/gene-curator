# PR444 fresh postmerge browser gate

Fresh `origin/master` at `785e573e4a0119f5c61e8bb5ee5a7438b889f4e3`, isolated Postgres5455/API8052/Vite5190. Canonical core passed **59/59**: every role, invitation restrictions, two review rounds, independent approvals, re-curation replacement and admin self-approval denial. No skipped assertions or prerequisite failures.

F narrow passed **9/9**. Actual UI displayed a finite custom total, expanded the warning card to show pinned-range and legacy nonfinite-string warnings with PMID wording, saved evidence and retained the total after reload. Authenticated API fixture setup used finite points999 plus a JSON-representable string `NaN` and clinical evidence missing a PMID. Two explicitly supplementary browser-origin authenticated GET assertions verified custom total-cap2, registry trace, finite raw1001 and two flags. Nonrepresentable numeric NaN/Infinity and structured recompute logging remain covered by unit/PostgreSQL tests.

Standalone F still has the existing fixed `/18` workspace presentation. New cap/category trace rendering belongs to unmerged E; it is not claimed here. The nonfinite row was excluded from scoring, finite out-of-range points were retained with a warning, and configured caps applied.

Local screenshots and JSON are ignored artifacts. No auth-state files or tokens copied. Reusable scratch runner `/tmp/w5F-postmerge-narrow.cjs`; earlier sanitized baseline runners restore from `../runner/`. API/Vite use fd9 closed and restricted scratch Vite filesystem access for fonts.

Actual loaded-font check passed1/1 (IBM Plex Sans).
