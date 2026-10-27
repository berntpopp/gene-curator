# Wave5 current checkpoint

> **OWNER STOP — shutdown checkpoint only.** Do not continue without an explicit resume. [Current handover](WAVE5-SHUTDOWN-HANDOVER.md) is authoritative: eight PRs merged, G fresh postmerge gate not run, J/I/R unmerged, no tag/release.

Eight functional PRs440/441/442/443/444/445/446/449 are merged with actual Opus/local+GitHubCI. Fresh postmerge gates are complete through446; G449
requires the FIRST fresh gate on resume. Master1215920. Epic264 and W4S266 are CLOSED
under accepted scope; original redesign cuts and excluded386 remain explicit.

J450/I451 remain open; G449 merged1215920 before STOP and its fresh gate has not run. All have actual Opus SHIP and full localCI; final parent
ancestry/PR metadata/GitHubCI/per-merge browser gates remain. Plan agent owns their
ancestry sync. Root orchestrates merges only. Exact heads and sessions are in the queue.

R final source06761a7 integrates Ifb24408 and differs in eight0.7.0 version files within backend/frontend; issue-template version text is updated separately.
Canonical fullCI passed at06761a7 (2572 FE/backend94.71%, fullPG,diff97/99%); fixture/docs/ignore actual review SHIP at01b6c77; last status/wording/bug-template delta review remains.
Earlier R320a338 passed226 browser checks with identical product behavior. Release452
stays draft; no tag or GitHub release. Every new merge still requires fresh browser gates.

Local monkey-stack.sh is a retained operator wrapper, precisely ignored, not release
tooling. Fresh clones must provision an isolated5455/8052/5190 stack explicitly.
Maintained tooling and unrelated root Wave3/4 changes are preserved. Heavy gates use
/tmp/gene-curator-wave5-gates.lock. Markdown evidence only; raw helpers/artifacts stay local.

See [report](WAVE5-REPORT.md), [review queue](WAVE5-REVIEW-QUEUE.md),
[integration ledger](W5R-INTEGRATION-CHECKPOINT.md), [epic audit](W5-EPIC-CLOSURE-AUDIT.md)
and [resume order](WAVE5-RESUME.md).
