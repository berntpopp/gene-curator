# W5G resumed lifecycle fixes

> Historical checkpoint entries below are retained for provenance. Current review, merge and gate status is in [the Wave5 report](WAVE5-REPORT.md); later entries supersede earlier pending statements.

PR [#449](https://github.com/berntpopp/gene-curator/pull/449) remains draft. Actual independent Opus 5.5 initial review at `cdc199c6f937022b590ccbb7663a0eeb071c3c42` returned SHIP (session `e2d6733c-aa33-4c18-b2c8-9a4b2867637e`), with two small lifecycle observations. That verdict does not cover subsequent fixes/integrations.

Native fix `28f3608` prevents a closing table batch from resetting a different caller's completed found/notfound result. Automatic retry watches the PMID set and editability, so unrelated score edits and row reordering no longer retry failed lookups. Explicit PMID blur still retries. Three regressions failed first; all 42 focused frontend cases pass afterward.

Test-only commit `57c76f8` adds six real app_user cases across submit/direct/bulk: inherited disease is checked before and after remote lookup. If a separate connection removes the linked disease during remote I/O, submission fails with the curation state unchanged; complete linked disease passes without copying it into evidence. The combined targeted PostgreSQL lane passed 39 tests. D's fallback stays network-free and uses the same-gene/same-scope link; G still refreshes authorization/content after remote work.

Full `make check` and canonical-lock `make ci` passed at `57c76f8b573e945e3d7824e4c295486fdb48ee69`, including 2,573 frontend tests, the full fresh-PostgreSQL lane and all standard static/type/security/build/repository gates. Backend coverage: 94.66%. Standard changed-line coverage: backend97% / frontend99%; isolated G against tested D parent `16b5285`: backend95% / frontend96%; lifecycle product fix alone100% (8 executable changed lines).

Final draft head `32b77d7d98b986cf2c028c2c6a44f6f74ae5c280` additionally includes the clean H/master `7b98416` merge. Post-H focused checks passed 60 backend, 107 frontend and 42 fresh-PostgreSQL tests. Per orchestration instruction, the full suite was not repeated for that independent parent merge; final current-master CI is required in later merge preparation. The required pre-push `make check` passed; remote draft449 matches the final head, working tree clean and branch remote comparison 0/0.

Only the initial G changes have an actual Opus SHIP. New lifecycle fixes and D/H integrations need the mandatory delta review after the CLI session limit resets or explicit owner signal; no retry or substitute review was attempted. Narrow UI checks also remain pending. D must clear its own review gate before G merges. No migration, historical evidence rewrite, new admin exception, RLS bypass, superuser role or role-switching path.

Local review input: `/tmp/w5-W5G-lifecycle-fix-delta.patch`. Local gate logs are `/tmp/w5-W5G-lifecycle-final-gates.log` and `/tmp/w5-W5G-h-integration-*.log`; these temporary artifacts are not release files. All worktrees and local evidence remain preserved.
