# Wave 5 browser evidence

Only sanitized Markdown reports are published here. All helper scripts, generated JSON results,
screenshots and HAR/auth-state artifacts under this directory are gitignored and remain local.
No auth-state files, JWTs, live tokens or passwords are published. Reports retain original `/tmp`
paths for provenance; references to scripts, JSON and screenshots describe local evidence, not repository
attachments. Their availability is not required to read the summarized findings.

| Snapshot | Result | Details |
| --- | --- | --- |
| `baseline/` | v0.6.0 at `a7538d1`; core lifecycle exercised, known #430 reproduced | Baseline failure is explicit in `w5-baseline-native-c7.json`. Initial harness failures are described separately from product observations. |
| `pr440/` | Fresh `4fe8b6d`: core 58/59, narrow 28/28, SQL view checks pass | The single core failure is unchanged #430; no disease-filter UI exists, so the API-only filter was tested with browser-origin authenticated fetch. |
| `pr441-candidate/` | Fresh `c51ad81`: core 59/59, corrected narrow 25/25 | Includes retained comment/request-changes capability and legacy zero-needed activation. Initial duplicate-assignment fixture mistake is preserved in the separate `review-harness-failure` JSON. |
| `pr441-postmerge/` | Fresh merged `7496d36`: core 59/59, narrow 27/27, font 1/1 | Full postmerge replay; two extra narrow checks create fresh reviewer invitations. |
| `candidateE/` | Fresh draft `01e85d7`: editable recovery 23/23, score trace 25/26 | Known excluded #386 qualitative mismatch retained; readonly local-display restore gap triaged into A guard fix. |
| `A-readonly-fix/` | Fresh `6cdc7ee`: narrow 12/12 | Readonly display stays authoritative; local draft preserved for later authorized restore. |
| `candidateJ/` | Fresh draft `e35ae58`: G PMID16/16, pagination5/5, H6/6; D/J original UI failures retained | Explicit-answer continuation and historical-pin correction are distinguished from original failures. |
| `candidateI/` | Fresh draft `62fe62e`: core59/59, clinical19/19, old-pin6/6, matrix57/57, scope17/17, pointer5/5, F7/7, font1/1 | Integrated candidate only; mandatory review/postmerge gates remain separate. |

All main workflow transitions were actual Chromium UI clicks: precuration approval, curation
submission, request changes, resubmission, independent approvals, re-curation and replacement
activation. API calls create fixtures or read state, except the explicitly identified legacy
review-submit edge. Isolated valid derived schemas exercise the same product paths without
changing published methodology versions. This is not clinical-score/default validation.

## Local reproduction

The Wave 5 helper scripts are local, ignored scratch tools; they are not included in the
release or required to read these reports. Script names and `/tmp` paths in reports identify
the original runs, not downloadable repository attachments. Local copies may be reused only
by their operator after checking the target snapshot, credentials and fixture state.

Use the existing orchestration tooling for a fresh isolated stack, with one browser owner,
Postgres 5455, API 8052 and Vite 5190. Keep server lock fd 9 closed and never use the development
stack. Preserve original failures separately from corrected fixture runs and narrow fix checks.

## Remaining baseline limitations

Seed accepted memberships have null `accepted_at`; fixtures establish accepted memberships via
real invitations. Newly created workflow pairs cannot configure `data_mapping` through the
current UI/API. A one-section derived schema renders no fields; fixtures use two valid sections.
Non-admin dashboard `/members` 403 noise and occasional Vuetify scroll warnings remain. Original
v0.6.0 screenshots used fallback fonts; #440 and #441 use the restricted font fix.
