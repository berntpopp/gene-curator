# W5D declared-default integration fix

Product commit: 4e7cf15519d51d2c8360895141756df9e88cb2d4 (isolated, native Codex).

Root cause: shared DynamicForm copied initial evidence but never materialized declared defaults. Boolean widgets displayed unchecked for absent values and emitted only after interaction, so required false defaults were missing from parent save/submit payloads. Correct required-field backend validation exposed this existing frontend gap.

Fix: initialize declared missing scalar defaults, including false/zero/empty/null, in editable forms before validation/emission. Recurse through object fields; skip readonly fields, arrays and evidence tables. Never infer false for an unspecified boolean. Preserve existing answers, loaded rows, parent input objects and deliberate edits. Late schema/data arrival and readonly/editable mode changes have regressions. Readonly form initialization never emits added defaults. Generated JSON schema now carries declared default metadata too.

Regression evidence: both curation map and precuration sections payloads failed before the fix. Focused 45 frontend tests, 5 generated-default tests, and14 PostgreSQL tests pass, including real app_user missing-answer refusal followed by explicit false save/reload/review for both stages. No backend validation relaxation or migration changes.

Integration: cherry-pick onto I/J/R. Preserve J's schema-generator metadata tuple containing description/default/default_by; D only adds default. DynamicForm changes are script-only, so preserve I's template and E's preview handling. I and ops received the commit; frontend ownership released.

Full canonical-lock CI running at this record's creation; independent browser recheck belongs to wave5_ops on the final combined candidate. Opus delta review remains pending due account spending cap. Draft445 remains draft.

Final gates at 4e7cf15: canonical-lock make ci PASS; 2,538 frontend tests, backend 94.65%, full fresh PostgreSQL lane, all static/build/repository gates. Fix-only coverage against ab050e58 is 100% backend and frontend. Logs: /tmp/W5D-defaults-ci.log and /tmp/W5D-defaults-diff-cover.log. Draft445 body updated; push pre-check underway. Opus delta/browser gates remain pending.
