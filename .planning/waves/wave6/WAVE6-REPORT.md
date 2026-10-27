# Wave 6 report: security and correctness, released as v0.8.0

Date: 2026-10-27. Master before: v0.7.0 (`217e704`). Released: v0.8.0 (`7abdbb9`).
Nine Wave 6 PRs plus a monkey-findings round, CI/Docker hardening, the CI concurrency fix and security dependency bumps.
Migrations 050-055.

## PRs

| PR | Issues | Content |
| --- | --- | --- |
| #460 | owner task | Docker: digest-pinned, non-root, multi-stage images; Trivy HIGH/CRITICAL gate; strict CI gate; weekly scan |
| #467 | #461, refs #374 | Seeded dev logins stripped from production builds; bundle spec greps the build output |
| #468 | #378, #373, refs #377 | NUL/oversized paths -> 400/414; client X-Request-ID reused; gene summary GETs no longer write |
| #472 | #380, refs #386 | Async sessions set the RLS user; scoring engine chosen from the schema (`engine_for`); bounded shutdown |
| #473 | #390-#393, #471 | Review actions on precuration detail; role-aware nav; design rules; public scope dashboard; schema picker labels |
| #474 | #376, #394, #379, refs #375/#386 | 050-054: outsiders see only active work; restrictive inactive-scope UPDATE policy; gene lookup indexes; `added_by` immutable |
| #475 | #448, #406, refs #453 | Curation lands on the scope's default pair; aria-disabled Submit; missing required fields reported |
| #476 | #399, #403 | Re-curation review diff against the replaced active curation; stage counts fixed; base64url token expiry |
| #477 | #469, #470 | Typed cell text commits after 400 ms and on Ctrl+S / leave; save indicator follows server state |
| #479 | (CI) | Draft runs can no longer cancel the ready run (concurrency group includes draft) |
| #488 | #483-#486 | Inactive-scope writes -> 409 on every path; `/edit` of active -> read-only; seeded memberships accepted (055); public scopes for non-members |
| #480, #481, #482 | alerts 234, 233 | msgpack 1.2.3, happy-dom 21.0.4, dnspython 2.9.0 |
| #487 | release | v0.8.0 notes, README upgrade section, version bump |

## Gates

- **Every PR:**
  - The implementer ran `make check` and `make diff-cover`.
  - An Opus ponytail-review, plus a delta re-review for each fix round.
  - Merged only on a green CI gate for the exact head commit.
- **Postgres lane:** `make test-postgres` on every PR touching SQL, RLS, sessions, saves or workflow.
- **Monkey tests on a fresh stack:**
  - v0.7.0: found #448 (major), #469, #470, #471.
  - Wave 6: found #483-#486, all fixed in #488 before the release.

## Decisions

- **MCP (#462):** fully authenticated. It can do everything the logged-in user may do, under the same RLS, D1 and capabilities. #463 was folded into #462.
- **LLM configuration (#489):** configurable in an admin console. Providers, encrypted write-only keys, immutable prompt versions, scope opt-in, `llm_runs` audit.
- **Weekly Docker scan:** kept as part of the owner's CI/CD hardening request.

## Process lessons

- **Draft-time runs:** commits pushed while a PR is still a draft get only skipped CI runs. `merge.sh` now judges the non-skipped run on the exact head SHA, and reopens the PR when none exists. One merge nearly used a green run from an older commit.
- **Wait loops:** never wait on `tail -2` of a background output file, because the exit line hides `MERGED`. Wait for `ALL-DONE`, or run the queue in one serial loop.
- **Fresh worktrees:** they must run `uv sync --extra dev --frozen` in `backend/`. Otherwise an old ruff reports false F811 errors.
- **Branch cleanup:** `git push --delete` runs the pre-push `make check` once per branch. Delete remote branches with `gh api -X DELETE .../git/refs/heads/<b>`.
- **Worktree removal:** removing a worktree with `--force` drops its ignored files. Check `git status --ignored` first (the pre-GSD ClinGen PDFs were restored from the Wave 5 backup).
- **Monkey tests:** they still find what reviews miss. Both rounds found real bugs after all PRs had passed review and CI.

## Follow-ups (open)

- **#478:** CORS on early 400/414 responses, the `gene_summaries` cache, rate limiting, admin-only HGNC repoint, non-ClinGen recompute.
- **#484 remainder:** `user_role` on single-scope GET; genes of active curations for outsiders.
- **#453:** a correction path for legacy disease gaps (owner decision).
- **#447:** segregation scoring (clinical design).
- **Redesign partials:** #273, #275, #276, #277, #278, #281.
- **Admin and permissions:** #216, #218, #219, #282, #284.
- **2024 backlog:** #86, #104, #105.
- **MCP/LLM epic #466:** #462, #489, #464, #465.
