# Wave 5 implementation and verification report

Status on 2026-10-22 after resumed actual Opus reviews: seven functional PRs are merged;
#449/#450/#451 and release [#452](https://github.com/berntpopp/gene-curator/pull/452) remain open.
The accepted methodology epic #264 and W4S #266 are closed after #446's fresh postmerge gate.
All functional fix/integration deltas have actual Opus5.5 SHIP verdicts. Final R source
`06761a7063cf491bd04188608edc30b037d88a84` differs from reviewed I only in eight intended
0.7.0 version files; its final full CI passed: 2,572 frontend tests, backend94.71%, full PostgreSQL and standard diff97/99%. R's latest fixture/docs/ignore delta
still needs actual review. No tag or GitHub release exists. GitHub PR metadata currently
lags some pushed branches; no merge proceeds on an unverified head or incomplete gate.

## Scope and decisions

The owner delegated decisions and requested end-to-end execution without further questions.
Scope is W4S (#429/#266/#264) and Wave 4 follow-ups #430–438. Root orchestrates only;
implementers use isolated worktrees and Ponytail full. Original exclusions remain:
#282, editable #284, #216, #218, #219, #105, #86, #104, #373–381, #386, #390–394,
#399, #403 and #406. Unrelated PR439 was untouched.

The clinical decision is an immutable successor: AR starting suggestions are 3 for two
null variants, 1.5 for null plus other (the SOP/GCI rounded convention), and 0.2 for two
other variants. Untouched/selector-only rows do not score. Every manual score edit,
including the same value, disables new-row suggestions; loaded rows are never managed.
Successor nested and legacy segregation require explicit points: missing points score
zero with a warning; deliberate zero is assigned and preserved. New rows start with
null points. Historical snapshots, pins, evidence, finite scoring and goldens stay unchanged.
[Clinical research and per-case rationale](WAVE5-CLINICAL-RESEARCH.md) use the actual
[ClinGen SOP v11 PDF](https://www.clinicalgenome.org/site/assets/files/9851/gene-disease_validity_standard_operating_procedures-_version_11_docx.pdf),
pages 17/20/21 and the segregation sections. Full pedigree/method automation is #447.

Migration 048 is merged in PR440; 049 belongs to PR450. Both are idempotent and
self-recording. The successor preserves customized, derived and edited definitions,
allocates the next available version and never overwrites published versions.
D1 includes administrators. No platform-admin RLS bypass was added. Affected workflow,
save and immutable-version changes have real API tests as app_user.

## Issue and gate ledger

Draft CI below means local `make ci`; GitHub CI is required before merge. Parent
integration and native fixes require the review deltas in the [queue](WAVE5-REVIEW-QUEUE.md).

| Issue                 | PR / final head                                                                   | State and evidence                                                                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| #431 catalogue        | [440](https://github.com/berntpopp/gene-curator/pull/440) / fdc745e               | Closed, merged 4fe8b6d; local/GitHub CI, diff 100%, actual Opus SHIP; fresh core 58/59 (known430), catalogue28/28                                                                      |
| #430 approval         | [441](https://github.com/berntpopp/gene-curator/pull/441) / c51ad81               | Closed, merged 7496d36; local/GitHub CI, diff 100%, actual Opus delta SHIP; fresh core 59/59+narrow 27/27                                                                              |
| #436 recovery         | [442](https://github.com/berntpopp/gene-curator/pull/442) / 9e048445              | Closed, merged 358ce6c; local/GitHub CI, diff 97%/fix100%, actual Opus delta SHIP; candidate 36+23, fresh core 59/font1                                                                |
| #432 derive           | [443](https://github.com/berntpopp/gene-curator/pull/443) / ccd90aa               | Closed, merged 7b98416; local/GitHub CI, diff 100%, actual Opus delta SHIP; fresh core 59+narrow 10+font 1                                                                             |
| #434 robustness       | [444](https://github.com/berntpopp/gene-curator/pull/444) / 62b7c35               | Closed, merged 785e573; local/GitHub CI, diff 97%, actual Opus delta SHIP/SOP PDF; fresh core 59+narrow 9+font 1                                                                       |
| #433 conditions       | [445](https://github.com/berntpopp/gene-curator/pull/445) /820bc706               | Closed, merged f9d6fa9; actual Opus delta SHIP, fullCI/check2564 FE/backend94.70%, diff99/100%; GitHubCI; fresh core59+D16+font1                                                       |
| #429/#266 trace       | [446](https://github.com/berntpopp/gene-curator/pull/446) /1e2a5c4                | Closed, merged182a66a; actual Opus SHIP; fullCI29091ca2546 FE/backend94.70%, diff99/98%, E-only97%; final tree identical; GitHubCI; fresh core59+E17+font1                             |
| #435 PMID             | [449](https://github.com/berntpopp/gene-curator/pull/449) /d0d4088 branch         | Open; actual Opus delta SHIP; fullCI15d6ea45,2555 FE/backend94.68%, fullPG,diff97/98%, G-only95/96%; final tree identical; PR metadata/GitHub gates pending                            |
| #438 AR decision      | [450](https://github.com/berntpopp/gene-curator/pull/450) /f1549c4 branch         | Open reviewed draft; actual initial PDF review+integration SHIP; fullCI2565 FE/backend94.72%, fullPG,diff97/97%, J-only99/100%; master ancestry/GitHub/postmerge gates pending         |
| #437 UI               | [451](https://github.com/berntpopp/gene-curator/pull/451) /fb24408 branch         | Open reviewed draft; actual exact-ID+integration SHIP; fullCI2572 FE/backend94.72%, fullPG,diff97/99%, I-only100/100%; master ancestry/GitHub/postmerge gates pending                  |
| #264 methodology epic | [446](https://github.com/berntpopp/gene-curator/pull/446) and prior accepted work | Closed after E fresh gate; all children265–271 closed under accepted scope. Original broader redesign and268 cuts are not claimed delivered; [closure audit](W5-EPIC-CLOSURE-AUDIT.md) |

Each draft passed its recorded check/push hook. Full CI includes fresh PostgreSQL,
static/type/security checks, coverage and production build. R focused integration checks
passed 84 backend and 156 frontend tests. See the [integration ledger](W5R-INTEGRATION-CHECKPOINT.md)
for exact source heads and manual conflict resolutions; combined gates are not assumed
from parent gates. No red merge, skipped test, suppressed failure or generated-type
formatting was used.

## Browser evidence and provenance

[Evidence index](wave5-evidence/README.md) links durable Markdown reports. Only isolated
Postgres 5455/API 8052/Vite 5190 were used, with server lock fd closed. UI interactions,
API fixture setup and browser-origin API supplements are identified separately.
The existing root workspace retains the machine-specific, ignored monkey-stack.sh wrapper.
It is operator-local tooling, not a release asset; a fresh checkout must provision the
isolated browser stack explicitly. Maintained setup/merge/restart tools remain tracked.
All seven merged slices have fresh postmerge gates. D passed core59+D16+font1;
E passed core59+E17+font1. A's expanded recovery36/36 and
existing23/23 were candidate checks; its postmerge replay was core 59/59 plus font 1/1.
H's postmerge core 59/59, narrow 10/10 and font 1/1 include API boundary checks explicitly.
F's narrow 9/9 includes two API trace readbacks alongside actual UI save/reload/warnings.

Earlier combined candidateI 62fe62e passed 171/171, including clinical19/19, old-pin6/6,
responsive57/57, scope/date/contrast17/17, pointer5/5 and warning/custom-cap7/7. Those
results predate the resumed D/E/G/I fixes and are historical candidate evidence, not a
claim that the new R candidate passed. The current combined replay passed226/226 at source320a338 without product changes.
[Combined browser report](wave5-evidence/R-combined/REPORT.md): core59, D16, E17,
G16+7, I6, clinical19, historical-pin6, responsive57, scope/review17, pointer5 and font1.
These are candidate integration checks; each future merge still needs its fresh gate.
The exact concurrent child-batch cancellation race is unit-tested, not claimed as
reproduced in the browser. Authenticated fixture/read-back API checks are labeled separately.
The prior trace25/26 result has only the explicitly excluded qualitative persistence386
failure. Original failing runs remain separately documented.

Only Markdown evidence is tracked. Screenshots, JSON and generated helper scripts remain
ignored local artifacts; counts change as browser work continues. Legitimate application
JSON and orchestration scripts are preserved. The release-candidate archive cleanup removed eight pre-GSD files and seven duplicate
legacy helper/cache files from R tracking while retaining every local byte, including SOP PDFs.
They remain tracked on current root master until the release integrates; ignore rules alone
do not untrack them.
Native factual audit confirms no tracked helper/artifact blobs or credential-pattern matches.

## Follow-ups, limitations and release

- Excluded [#386](https://github.com/berntpopp/gene-curator/issues/386): qualitative preview
  StrongAssociation/10/no trace can save as no_known/0/ClinGen cap18. No qualitative
  persistence parity is claimed. Supported ClinGen/custom trace presentation remains scoped.
- [#447](https://github.com/berntpopp/gene-curator/issues/447): family/method-aware automatic
  segregation. Historical v1 heuristics may over-score; no historical rescore or repin.
- [#448](https://github.com/berntpopp/gene-curator/issues/448): first-active workflow-pair
  selection may ignore scope default. Adjacent to excluded216; no asserted duplicate.
- Free-text MONDO human-disease suggestions omit some susceptibility entities outside that
  ancestry branch. Exact canonical ID lookup preserves stored labels without remapping or
  additional requests. New exact-ID fix still needs its actual Opus delta review.
- Pending invitations with accepted_at null grant nothing. Catalogue options retain the
  existing unordered limit50. Local recovery retains one draft per record, with competing
  tabs last-writer-wins and exact-snapshot cleanup.

Master is182a66a. Eight active project version files are0.7.0; old0.6.0 references in
historical release/README/milestone text remain intentional. README documents048/049.
Release claims cite their PRs.
Independent native factual audit at docs2fa74d7/source320a338 found no corrections:
all eight active versions, PR citations, gate counts and review provenance matched;
37 Markdown files had valid relative links, 20 evidence files were Markdown-only,
credential-pattern matches were zero, and 860 source/config ignore probes matched none.
This factual audit is supplementary and does not approve product changes or replace Opus.
Release452 remains draft; no tag/release has been created.
R actual integration/release SHIP at453a49b and cleanup delta SHIP ate02479b are recorded
in sessionb09f17b0-07b0-4e07-bb88-b14dedb9c10b. Latest fixture/docs/ignore changes still
need a narrow actual delta review. Before publication all functional PRs must merge individually after actual review/local
and GitHub CI/fresh UI gates. R must then have only intended release/version changes or
explicitly reviewed integration fixes relative to master, and pass its own actual Opus
review and final gates. See [resume checkpoint](WAVE5-RESUME.md) and [Wave6 prompt](WAVE6-PROMPT.md).
