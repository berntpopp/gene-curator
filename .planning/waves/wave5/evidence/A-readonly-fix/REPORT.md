# Readonly local recovery guard

Commit `6cdc7ee` on A, after merging master7496d36 and the fixture-only review-test correction. Local full CI, make check, diff check, and pre-commit checks passed. Backend coverage94.62%;215 frontend files/2484 tests; frontend changed-line coverage97%. The existing real app_user PostgreSQL save-conflict/reopened-explicit-restore regression remains and passed.

The new form-flow regression failed before the fix because a recovery control existed during readonly review. It then passed with the guard;31 focused tests passed. The regression also exercises a late restore action after readonly changes and confirms local recovery storage is not cleared.

The fix hides the recovery control while readonly and independently guards the action. It does not change saving or server authorization.

Fresh isolated stack at exact6cdc7ee, actual Chromium UI narrow recheck: **12/12 pass**, zero fatal errors. One tab edits locally, another submits the curation through UI. Reload shows readonly server evidence, no restore control, disabled Save, and preserves the exact local snapshot. An independent reviewer requests changes through UI; after reload the author can explicitly restore the preserved local draft, save through API via UI, and reload the saved evidence.

Original failure is retained under candidateE: restore changed the readonly local evidence display, while making zero curation write requests and leaving stored evidence/lock unchanged. This was a display-integrity defect, not an observed write bypass. Existing baseline recovery also lacked a readonly guard; A's cross-tab recovery made the scenario reproducible.

The first full CI attempt reached the repository file-size gate and failed for an oversized test file. Test spacing was compacted without removing assertions; the final complete CI run passed. No allowlist or test gate was weakened.

No Opus delta review is claimed: Claude spending limit remains exhausted. PR442 remains a draft; no ready/merge attempted. This is candidate narrow evidence, not a postmerge full-stack gate.
