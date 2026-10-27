# W5D inherited disease review fix

Owner resumed Wave 5 on 2026-10-22. PR [#445](https://github.com/berntpopp/gene-curator/pull/445) remains draft.

Actual Opus 5.5 initial review at `4e7cf15519d51d2c8360895141756df9e88cb2d4` returned FIX (session `c01a6d5e-4428-4680-9912-f09d92c1045e`). Required readonly disease fields blocked direct-created or historical curations even when their linked precuration held the disease. The reviewer also requested actual app_user ACTIVE-to-REVIEW refusal coverage.

Native fix `31242e8` validates a temporary evidence view using the existing disease field helper. Only the linked precuration for the same gene and scope can supply absent disease fields; ordinary app_user RLS still applies. Explicit own values, including empty/null answers, win. No saved evidence, methodology snapshot, permission policy or migration changes.

Regression evidence:
- Before the product fix, all six valid flat/nested linked-disease combinations failed through submit, direct transition and bulk. Three focused unit cases also failed.
- After the fix, 22 fresh-PostgreSQL API cases and 19 unit tests pass. The matrix includes absent disease, refused-state preservation and ACTIVE-to-REVIEW rejection. Unit cases cover own values, blanks/nulls, malformed parents, scope/gene mismatch and no evidence mutation.
- Test fixtures publish a separate successor snapshot instead of editing an existing pin. The API uses app_user; owner connections only seed fixtures and inspect persisted state.

F/master integrated cleanly at `bbd7f1b7f60086805ea751d94f1e4b1ffd67321b`. The first check run was deliberately stopped before CI when A became imminent; it is not claimed as a passed gate. A/master integrated at final candidate `16b5285989e125e82f89989fa84d957a48e918d9` (master `358ce6c`). Final `make check` and canonical-lock `make ci` pass: 2,564 frontend tests, full fresh-PostgreSQL lane and all standard gates, backend coverage 94.69%. Changed-line coverage: backend 99%, frontend 100%; inherited-disease fix alone 100% (13 executable lines). Narrow UI verification and mandatory actual Opus fix-delta review remain pending. No further Opus attempts before the session reset or explicit owner signal.

Local delta artifact: `/tmp/w5-W5D-inherited-fix-delta.patch`; initial review: `/tmp/w5-root-D-initial-review.json`. The patch is local review input, not a release artifact. Full source is not reproduced here.
