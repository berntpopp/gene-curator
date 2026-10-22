# Wave 5 resume checkpoint

> **12:31 UTC update:** actual Opus reviews resumed successfully, then the CLI hit its session usage limit (reset 19:00 Europe/Berlin). Completed SHIP verdicts remain valid; no further calls before reset. Native fixes and already-reviewed merge/browser gates continue.

**Owner resumed work on 2026-10-22.** A single actual Claude Opus 5.5 probe returned
OPUS_READY with is_error=false and modelUsage claude-opus-5-5. Required independent
Opus reviews are restarting from the saved queue. No billing/auth changes or substitute
approvals are authorized. All previously recorded gates and exclusions remain binding.

- Release draft: [#452](https://github.com/berntpopp/gene-curator/pull/452), branch `release/v0.7.0`.
  Last cleanup head before this documentation checkpoint: `985063af3927935d94fffb72622c3ef5292085e1`.
  The checkpoint commit is the commit adding this file; obtain its full SHA with
  `git log -1 --format=%H -- .planning/WAVE5-RESUME.md` (also recorded in the final handoff).
- Master: `7496d3663e68b91c53263337d4ee0c936f176b49`; PRs #440 and #441 are merged.
- Eight implemented functional drafts remain: #442, #443, #444, #445, #446, #449, #450, #451.
  Mandatory independent Opus ponytail reviews have resumed; native reviews do not replace them.
- Local required gates passed. Combined candidate `62fe62e` passed 171/171 browser checks.
  These candidate results do not replace future per-merge checks. No v0.7.0 tag/release exists.
- All generated Wave 5 helpers/artifacts are ignored; evidence tracks Markdown only.
  Eight obsolete archive files are untracked but retained locally, including SOP PDFs.
  Deliberate Markdown, planning configuration and established orchestration tools are preserved.
- Preserve every worktree. Ops owns isolated test servers and fresh post-merge browser gates.
  Do not touch the development stack or discard local work.
- Root has pre-existing dirty planning/tooling, local `.gitignore` changes and untracked duplicate
  Wave 5 documents. Reconcile only verified task-owned duplicates before a future fast-forward;
  preserve unrelated Wave 3/4 edits and local ignored evidence.

## Resume order

1. Read [report](WAVE5-REPORT.md), [review queue](WAVE5-REVIEW-QUEUE.md) and
   [Wave 6 prompt](WAVE6-PROMPT.md); verify current remote heads and owner-resume authorization.
2. When Opus is actually available, complete each required review; fix rounds review only the
   delta and connected behavior. Clinical reviews must use the actual SOP v11 PDF.
3. Update each candidate against current master, run required local/GitHub CI, then merge one PR
   at a time via `set -o pipefail; merge.sh N | tail`. Never merge red or bypass reviews.
4. After each functional merge, use a fresh isolated stack for every role, two review rounds and
   re-curation in the UI. After fixes, narrowly recheck that exact flow in a real browser.
5. Reconcile the release draft, fact-check notes/versions, complete its Opus/CI gates, then release
   only after all mandated gates pass. Refresh the final report and continuation prompt.
