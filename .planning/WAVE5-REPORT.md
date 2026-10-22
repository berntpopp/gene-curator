# Wave 5 implementation and verification report

Status: release blocked by required Opus reviews. Two PRs are merged; eight functional
PRs are implemented as drafts. The v0.7.0 release candidate is prepared and has passed
local CI. Final browser checks passed171/171; the release draft link is being recorded below.

## Scope and decisions

The owner delegated decisions and requested end-to-end execution without further
questions. Scope is W4S (#429/#266/#264) and Wave 4 follow-ups #430–438. Root only
orchestrated; implementers used isolated worktrees and Ponytail full.

Original exclusions remain: #282, the editable part of #284, #216, #218, #219, #105,
#86, #104, #373–381, #386, #390–394, #399, #403 and #406. Unrelated PR439 was untouched.

The clinical decision is a new immutable successor, with selector-specific AR starting
scores and explicit curator-entered segregation points. Existing published snapshots,
pins, evidence and finite historical golden expectations remain unchanged. Untouched
successor segregation points start unassigned; an intentional zero stays zero.
[Clinical evidence and case rationales](WAVE5-CLINICAL-RESEARCH.md) cite the actual
ClinGen SOP v11 PDF. Full automatic pedigree scoring remains [#447](https://github.com/berntpopp/gene-curator/issues/447).

Migration048 belongs to catalogue PR440. Migration049 publishes the successor in PR450;
it is idempotent, self-recording and preserves customized/derived methodologies.
D1 and app_user RLS remain enforced; no superuser/BYPASSRLS or platform-admin bypass
was introduced. Existing explicit admin edit policies were preserved.

## Issue and gate ledger

For drafts, CI means local `make ci`; required GitHub CI is deferred until ready.
Changed-line coverage below is the reported task-specific result where available.
Every remaining PR still needs actual Opus review, current-master integration checks,
required GitHub CI and its fresh postmerge browser gate. Native review is supplementary.

| Issue | PR and tested head | State | Local gates / review |
| --- | --- | --- | --- |
| #431 catalogue | [440](https://github.com/berntpopp/gene-curator/pull/440), fdc745e | Closed, merged4fe8b6d | CI/check, diff100%; Opus SHIP; GitHub CI passed |
| #430 reviewer approval | [441](https://github.com/berntpopp/gene-curator/pull/441), c51ad81 | Closed, merged7496d36 | CI/check, diff100%; Opus delta SHIP; GitHub CI passed |
| #436 recovery | [442](https://github.com/berntpopp/gene-curator/pull/442), 6cdc7ee | Implemented draft | CI/check, diff97%; final Opus delta pending |
| #432 derive/race | [443](https://github.com/berntpopp/gene-curator/pull/443), fad565a | Implemented draft | CI/check, diff100%; final Opus delta pending |
| #434 scoring robustness | [444](https://github.com/berntpopp/gene-curator/pull/444), 5968924 | Implemented draft | CI/check, diff97%; all five review findings fixed, Opus delta pending |
| #433 condition parity | [445](https://github.com/berntpopp/gene-curator/pull/445), 4e7cf15 | Implemented draft | CI/check, 2538 frontend tests; initializer fix diff100%/100%; Opus pending |
| #429 / #266 score trace | [446](https://github.com/berntpopp/gene-curator/pull/446), 01e85d7 | Implemented draft | CI/check, 2530 frontend tests; E-only diff96%; Opus pending |
| #435 PMID/workflow | [449](https://github.com/berntpopp/gene-curator/pull/449), cdc199c | Implemented draft | CI/check, 2536 frontend tests; G-only diff95% backend/96% frontend; Opus pending |
| #438 AR defaults | [450](https://github.com/berntpopp/gene-curator/pull/450), 6fbddc4 | Decision recorded, implemented draft | CI/check, 2547 frontend tests; J-only diff99%/100%; Opus pending |
| #437 UI polish | [451](https://github.com/berntpopp/gene-curator/pull/451), 62fe62e | Implemented draft | CI/check, 2561 frontend tests; I-only frontend diff100%; Opus pending |
| #264 methodology epic | #446 and dependencies | Partial until merged/verified | Accepted Wave4 scope reductions remain; original broader requirements are not claimed delivered |

Backend PostgreSQL lanes use the real API as app_user for affected saves, review entry,
locks, permissions and immutable version flows. Heavy gates and setups were serialized.
No red merge, skipped test, suppressed CI failure or generated-type formatting was used.
An independent native Ponytail review of the I-owned delta at62fe62e found no actionable
issue (SHIP for that delta only). It excluded the reviewer's own D/J changes and does not
satisfy the required Opus gate. The exact remaining queue is in
[WAVE5-REVIEW-QUEUE.md](WAVE5-REVIEW-QUEUE.md).

## Browser evidence

Only isolated ports5455/8052/5190 were used, separate from the dev stack. Server lock
file descriptors were closed. [Evidence index](wave5-evidence/README.md) distinguishes
actual UI actions, API fixture setup and supplementary browser-origin API checks.

- PR440 fresh postmerge: core58/59, with only the known430 failure; catalogue narrow28/28.
  There is no disease-filter UI control; API filter checks supplemented actual UI display.
- PR441 candidate: core59/59 and narrow25/25. Fresh postmerge: core59/59 and narrow27/27.
  Already-approved reviewers retained comments/Request changes; legacy activation worked.
- Recovery: editable23/23. A further read-only restore action changed displayed evidence
  without a server write; its fix passed fresh12/12, including later authorized restoration.
- Trace:25/26, with the sole parity failure exactly matching excluded386. Custom caps,
  selected rules, pinned saved traces and delayed responses passed.
- G PMID16/16 and pagination5/5; H Derive6/6; historical-pin preservation6/6.
  Pagination used102 legitimate API-created histories and actual UI re-curation.
- Earlier combined J core exposed omitted declared-false defaults in both forms.
  Original failures are preserved. The shared initializer fix retains explicit values
  and read-only evidence; fresh final I62fe62e core passed59/59 without workarounds.
- Corrected successor AR/segregation UI checks passed19/19. Old immutable-pin checks6/6.
- I responsive matrix57/57 at1440/390 in light/dark; scope/queue/date/contrast17/17.
  Local scrolling, read-only values, editable return and real Save pointer timing passed.
  The actual font loaded. One scoped Impeccable detector pass found no issue; this is
  supplementary evidence, not accessibility certification.
- Final blocker-during-pointer5/5, scoring warnings/custom cap7/7 and fonts1/1 passed.
  The final candidate suite totals171/171. F used actual UI warning expansion/save/reload
  with a JSON-representable NaN string; nonrepresentable values/logging remain unit/PG
  checks. These are candidate checks, not substitutes for future postmerge gates.

The owner requested artifact cleanup. Screenshots, browser-result JSON, HAR and named
session-state files under `.planning/wave5-evidence/` are locally retained and ignored.
At the final audit126 generated files were ignored; none were tracked or staged.
Application JSON, lockfiles and Markdown reports remain eligible. Release staging
contains only sanitized Markdown reports and reusable runner sources from that directory.

## Follow-ups and limits

- Excluded [#386](https://github.com/berntpopp/gene-curator/issues/386) remains: qualitative
  preview returned Strong Association/10/no trace, while saving produced no_known/0/a
  ClinGen cap18 trace. The baseline unconditional save dispatch was verified; no qualitative
  persistence parity is claimed.
- Historical v1 automatic segregation can over-score some inputs. The successor contains
  this with explicit points; no historical scores were rewritten. Full automation is #447.
- [#448](https://github.com/berntpopp/gene-curator/issues/448) records first-active workflow-pair
  selection ignoring the intended scope default when pairs share a precuration schema.
  It is adjacent to excluded216, not an asserted duplicate.
- Human-disease MONDO suggestions omit susceptibility terms outside that ancestry branch.
  Existing selected/stored identifiers remain intact; no name heuristic or remapping.
- Seeded memberships with accepted invitation status but null accepted_at were observed;
  they still grant nothing and were not silently repaired.
- Catalogue options retain the pre-existing unordered limit50. Local recovery retains one
  draft per record; competing tabs remain last-writer-wins, with exact-snapshot cleanup.
- Excluded406 and other excluded issues are not claimed fixed. #268 remains partial under
  the accepted methodology cut; no language/expression/expert-panel expansion was added.

## Release, sync and blocker

Root master is synchronized to origin/master7496d366. All completed functional branches
are pushed as drafts. Pre-existing root planning/tooling edits were preserved; the
requested narrow .gitignore update is also present locally and in the release candidate.

The release/v0.7.0 candidate passed local check/CI. Eight active version files were audited
and bumped: backend init/constants/pyproject/uv.lock and frontend package/package-lock/
AppBar/version test. Retained0.6.0 references are historical README/release/milestone
references; package-lock ^10.6.0 is an unrelated dependency constraint. README explains
048/049 upgrades and unchanged historical pins. Every release-note claim cites a PR.
A separate native factual audit verified citations, versions and clinical limitations.

Release PR: [452](https://github.com/berntpopp/gene-curator/pull/452), draft. No v0.7.0 tag or GitHub release
has been created. Claude Code Opus5.5 hit the account monthly spend limit; incomplete
review calls yielded no verdict. Mandatory reviews cannot be replaced by native reviews.
No billing/authentication changes or retry loop were attempted. Remaining merges and
publication are blocked on that review gate, not reported complete.

## Wave 6 continuation

Use [WAVE6-PROMPT.md](WAVE6-PROMPT.md). Finish the recorded Wave5 review/merge/release
queue before selecting new scope. The owner requested no further questions.
