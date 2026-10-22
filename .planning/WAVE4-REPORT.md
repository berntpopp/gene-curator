# Wave 4 report: methodology epic (#264), released as v0.6.0

Dates: 2026-10-21 to 2026-10-22. Master before: v0.5.0 (`9689149`). Orchestrated: 22 PRs, migrations 042-047,
7 monkey rounds on a fresh isolated stack (Postgres 5455 / API 8052 / Vite 5190).

## Issues

| Issue | State | PRs |
| --- | --- | --- |
| #265 Methodology versions: immutable versions, pinning, provenance, derive | closed | #407, #410, #412, #420 |
| #267 Form interpreter (field registry, steps, conditions, evidence table) | closed | #415, #421, #425, #426, #427, #428 |
| #269 Methodology language (shrunk: JSON/YAML + validator + static checks) | closed | #413, #419 |
| #270 Methodology tests, score trace, upgrade impact | closed | #419 |
| #271 Derived methodologies (shrunk: derived_from pointer + derive) | closed | #412 |
| #408 Validator ignored list-shaped rules | closed | #413 |
| #409 Re-curation duplicated fields, dropped precuration link | closed | #411 |
| #266 One scoring interpreter | partial (backend done; frontend trace display = W4S) | #416, #417, #419, #420, #423 |
| #268 Workflow interpreter | partial (transitions + reviewers_required from pinned version; expert-panel stage, effects, expression language cut by owner) | #414, #418 |
| #264 Epic | open until W4S | all of the above |

## PRs and gates

Every PR: implementer `make check` + `make diff-cover` (90% changed lines); Opus ponytail-review plus delta re-review
per fix round; merged through `merge.sh` only on a green, up-to-date `CI gate`. `make test-postgres` additionally on
every PR touching SQL, RLS, triggers, workflow or saves.

| PR | Content | Postgres lane |
| --- | --- | --- |
| #407 | 042 methodology_versions, immutable publish, pinning trigger, backfill, admin publish/list | yes |
| #410 | 043 TRUNCATE guard | yes |
| #412 | 044 derive + versions readable by active users | yes |
| #411 | Re-curation prefill + current approved precuration link | n/a |
| #416 | Point-model scoring interpreter (158 golden cases, 0 diffs vs old engine), pinned scoring, recompute pinned | yes |
| #415 | components/dynamic: field registry, steps, conditions, evidence_table | n/a |
| #414 | 045 drop workflow trigger; transitions + reviewers_required from pinned version; hidden required fields | yes |
| #413 | One validator, list rules (#408), static checks incl. point_model shape | yes |
| #417 | Detail page + approve dialog show stored scores, caps from trace | n/a |
| #418 | Hidden show_when fields don't block precuration submit; multi-reviewer approve message | yes |
| #419 | Publish gate (422), version tests, score trace, impact preview | yes |
| #420 | 046 ClinGen v1 corrected in place; SOP v11: Models+Rescue cap 4, case-control summed cap 12, AR other-variant proband 3; recompute report | yes |
| #421 | Forms render from the pinned version; components/clingen deleted; live score from validate-evidence | n/a |
| #422 | App footer; far fewer warnings in one compact card; live score panel; scored rows without PMID | n/a |
| #423 | 047 contradictory evidence disputes only by Impact "disputed"; working copy synced | yes |
| #425 | Escape stays in fields (curation + precuration); unknown-PMID reason beside Submit | n/a |
| #426 | Saved PMIDs checked when a table loads | n/a |
| #427 | Server refuses review with unknown PMIDs on every path (submit, transition, bulk); point ranges on every path; capped lookups | yes |
| #428 | Save draft never moves when the save-state label or blocker text changes | n/a |
| #424 | Release v0.6.0: notes, README upgrade section, version bump | CI |

## Owner decisions

- #269 shrunk: no methodology language. #271 shrunk: derived_from_version_id + derive only.
- All planner cuts accepted: no expert-panel stage, no assign/recurate effects, no expression language, ClinGen item
  adapter stays, GenCC/qualitative engines stay, no sha/reason/methodologies table, impact preview only (no apply).
- ClinGen v1 drift: fix v1 snapshots in place (046, and 047 for the contradictory rule), owner-run, logged; pins never move.
- SOP v11 corrections in 046: Models+Rescue one category cap 4; case-control single-variant + aggregate summed, cap 12;
  AR other-variant up to 3 per proband.
- Contradictory evidence: Disputed only when a row's Impact is "disputed".
- Footer: bottom of the window on short pages, after the content on long pages.
- Silent 0-row UPDATE/DELETE of a published version as app_user counts as "fails" (owner path raises).

## Deploy note (v0.6.0)

Apply migrations 042-047 (`make db-migrate`), then run `make recompute-scores` once; it logs every curation whose
total or class changes. Re-label old contradictory rows that really dispute a curation (Impact "disputed").

## Process lessons

- Monkey tests found what reviews missed in every round (live score never rendered, unknown PMID submittable via
  reload, Save click lost to a layout shift). Run the narrow re-check after every fix, in a real browser.
- Shared JSON key order is lost in jsonb: config needs explicit `order`.
- merge.sh: pipe with `set -o pipefail`, otherwise a failed merge still runs the cleanup chain; it can also give up
  when a PR leaves draft and CI has not started yet (re-run it).
- Never put backticks inside double-quoted setup.sh notes (the shell executes them).
- Clinical scoring changes need the SOP PDF checked by the reviewer, not the implementer's memory.

## Follow-ups (to file as issues)

See `.planning/WAVE4-SLICES.md`, "Follow-ups collected in Wave A", minus items resolved in this wave. Open items:
W4S frontend score trace (#266); approve button for a reviewer who already approved (reviewers_required > 1);
catalogue disease filter reads top-level disease_name only; 003 view reads a never-written score key; derive toast and
SchemaEditor label; duplicate schema names race; required_when not enforced by the backend and condition-evaluation
edge cases; recompute skips custom categories; precuration fetch paging for re-curation; EvidenceTable CSS.escape;
AR blank-row defaults per variant (owner call); 046 custom-model Postgres test; scorer does not clamp single rows;
PMID warning wording for not-counted points; PMID lookup batch size vs 10 s timeout; submit holds the row lock during
lookups; "Restore unsaved changes?" can overwrite newer server data; UI polish (table widths at 1440, clipped chips at
390, input-styled read-only evidence, MONDO animal diseases, UTC invite dates, sticky Save/Submit bar).
