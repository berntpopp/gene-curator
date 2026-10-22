# Wave 5 local browser runners

These helpers are local ignored evidence, not release assets. They require Playwright from the isolated monkey worktree and `W5_TEST_PASSWORD` supplied through the environment. No auth states or tokens are stored here. Restore the `.cjs` helpers and `w5-baseline-vite-server.mjs` to `/tmp` before use; helpers refer to each other by that scratch path.

This existing workspace retains `.planning/orchestration/monkey-stack.sh` as an ignored,
operator-local wrapper with machine-specific paths. It is not a maintained release tool
and is absent from a fresh clone. Provision an isolated Postgres/API/Vite stack explicitly
when reproducing from another checkout; never substitute the dev stack. The maintained
`make test-postgres` lane remains reproducible from tracked repository tooling.

Here, fresh stack resets use that retained local wrapper under `/tmp/gene-curator-wave5-gates.lock`, with fd9 closed. Use only DB5455/API8052/Vite5190. Preserve dev5454/8051/5193. Start retained API/Vite sessions after setup if transient launch processes were reaped. The scratch Vite config allows the exact root dependency directory for fonts; it does not disable filesystem protection globally.

After a fresh DB, delete only old `/tmp/w5-baseline-state-*.json` browser states. Run `w5-baseline-bootstrap-core.cjs`, then `w5-baseline-run-all.cjs` with `W5_REPORT` pointing to a unique ignored JSON path. The core has59 checks over11 phases, every role, two review rounds and re-curation. A fresh bootstrap is required for every canonical replay.

Focused runners:

- `w5H-postmerge-narrow.cjs`:10 derive/null-guard checks, no core fixture needed. The filename is historical; reports must name the actual tested candidate or merged SHA. Run once per fresh DB because deriving the same next version again is intentionally rejected.
- `w5-candidateE-bootstrap.cjs`: set `W5_FIXTURE_TYPES=trace` for the custom trace fixture only; requires core IDs. API fixture creation is distinguished from UI workflow assertions.
- `w5F-postmerge-narrow.cjs`: custom finite score/warnings/save/reload;9 checks with labelled API supplements.
- `w5a-precuration-readonly.cjs`, `w5a-expanded-curation.cjs`, `w5a-late-save-cancel.cjs`: A recovery36 checks; require core and custom trace fixtures. Focus form tab before Escape so the event reaches the actual form handler.
- `w5-candidateE-recovery.cjs`:23 editable recovery checks. Run after readonly/cancel fixtures have returned to authorized editing.
- `w5E-pending-layout.cjs`: prepared new E pending-layout/timing narrow; actual preview responses are held and released, then one controlled503 checks pending termination. Must run on a candidate containing the pending-layout fix.
- `w5I-exact-mondo.cjs`: prepared new I stored-ID label narrow; uses an authentic derived precuration schema and real ontology endpoint. It depends on the external ontology service and should report availability failures honestly.

Historical E trace runner expects the old aside disappearance behavior and includes known excluded386 qualitative parity failure. Do not reuse that obsolete timing assertion for the pending-layout fix. Use the new narrow runner instead, preserving historical evidence separately.

Do not copy auth state or scratch IDs into tracked files. JSON/screenshots/HAR/helper code are ignored. Markdown reports distinguish candidate evidence from mandatory fresh postmerge gates, expected422 diagnostics from failures, and browser-origin API supplements from UI clicks.
