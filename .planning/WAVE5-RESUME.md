# Wave 5 resume checkpoint

**Owner-paused on 2026-10-22.** The owner requested stopping because Opus is unavailable.
Do not resume implementation, reviews or queued work until the owner explicitly resumes.
No further Opus calls, billing/auth changes or substitute approvals are authorized.

- Release draft: [#452](https://github.com/berntpopp/gene-curator/pull/452), branch `release/v0.7.0`.
  Last cleanup head before this documentation checkpoint: `985063af3927935d94fffb72622c3ef5292085e1`.
  The checkpoint commit is the commit adding this file; obtain its full SHA with
  `git log -1 --format=%H -- .planning/WAVE5-RESUME.md` (also recorded in the final handoff).
- Master: `7496d3663e68b91c53263337d4ee0c936f176b49`; PRs #440 and #441 are merged.
- Eight implemented functional drafts remain: #442, #443, #444, #445, #446, #449, #450, #451.
  Mandatory independent Opus ponytail reviews remain blocked; native reviews do not replace them.
- Local required gates passed. Combined candidate `62fe62e` passed 171/171 browser checks.
  These candidate results do not replace future per-merge checks. No v0.7.0 tag/release exists.
- All generated Wave 5 helpers/artifacts are ignored; evidence tracks Markdown only.
  Eight obsolete archive files are untracked but retained locally, including SOP PDFs.
  Deliberate Markdown, planning configuration and established orchestration tools are preserved.
- Preserve every worktree. Ops is assigned to stop only isolated test servers and retain the DB.
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
