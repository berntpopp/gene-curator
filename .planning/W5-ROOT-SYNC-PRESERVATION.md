# Root workspace preservation before final release sync

Snapshot taken 2026-10-22 while GitHub's PR/Actions incident delayed final merges.
Root HEAD: `182a66a1179faf845fed8f3627eb16ee0c87c401`.
Release candidate: `06761a7063cf491bd04188608edc30b037d88a84`.
Recompute the deletion list and refresh changed files immediately before an actual sync: R is still active.

## Verified backups

- Temporary: `/tmp/gc-wave5-root-preservation-lpdnftfn`
- Durable outside repository: `/home/bernt-popp/.local/state/gene-curator/backups/gc-wave5-root-preservation-lpdnftfn`
- Each contains `manifest.json`, `SHA256SUMS` and exact relative paths under `files/`.
- 70 files / 16,147,612 bytes; every copied file's SHA-256 was verified in both copies.
- Categories: 15 release deletions, six dirty tracked files, 48 unique untracked planning Markdown files, one maintained untracked `monkey-stack.sh`.
- Selection excluded runtime evidence, auth state, cookies, environment files and credentials. Private-key/provider-token/JWT pattern scan found no selected credential material. No values were printed.
- No root files were reset, stashed, cleaned, deleted or replaced during backup.

The 15 deletions are the archived `.ui-ux-review-iterations` state plus seven files in each of the old `.planning/milestones/pre-gsd/plan/scripts/` and `plan/scripts/` trees: downloader, requirements, downloaded HTML and four PDFs. Their filenames and byte hashes are in the manifests. Deliberate planning documents and maintained orchestration scripts are preserved.

The six dirty tracked files are `.gitignore`, `.planning/ORCHESTRATION-WAVE3.md`, the archived scripts README and ClinGen INDEX, `.planning/orchestration/rules.md`, and `.planning/orchestration/setup.sh`. The maintained untracked monkey-stack helper is separately preserved. Existing user edits must survive the eventual sync.

## Eventual reconciliation procedure (not executed)

1. Pin final release/master SHA, inventory root status and all release deletions again. Refresh backups for changed/new files, verify hashes, and retain this older snapshot rather than overwriting it.
2. Compare incoming tracked paths against untracked local files. Keep byte-identical collisions in verified backup before moving only those collision files aside. For differing planning reports, retain both versions and deliberately reconcile current authoritative evidence; never blindly restore an older report over a newer one. Leave noncolliding files untouched.
3. Compare each of the six dirty tracked paths with incoming content. Preserve unrelated edits in place if Git can carry them forward. For actual overlapping blockers only, save their current bytes and baseline patch outside the repository, verify the backup, then reconcile deliberately. Avoid blanket reset/stash/clean commands or whole-directory replacements.
4. Fast-forward only after all required PR/CI/browser/release gates and ancestry checks pass. No force update and no implicit merge of unrelated history.
5. Restore the 15 deliberately untracked helper/cache/PDF files from the latest backup to their original local paths only where absent, verify every restored hash and `git check-ignore` them. They remain local, never restaged. Preserve newer local copies if any exist; compare rather than overwrite.
6. Verify all original user edits, planning reports and maintained scripts survived; verify no auth state/runtime artifacts entered tracking, no product path is accidentally ignored, and root/release status and version/tag metadata match the intended handoff.

This plan does not authorize early release publication, bypass review gates, or claim that the current release candidate is final.
