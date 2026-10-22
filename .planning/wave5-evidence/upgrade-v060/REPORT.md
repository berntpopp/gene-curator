# Populated v0.6.0 upgrade rehearsal

**PASS**: genuine v0.6.0 database upgraded in place through048/049 to reviewed product `06761a7063cf491bd04188608edc30b037d88a84`. Only isolated Postgres5455/API8052/Vite5190 was used. No product edits, dev-stack access or full226-check replay. The same database container/volume remained in use across migration and application checkout.

## Prior evidence and the missing path

`backend/tests/postgres/test_clingen_successor.py` already covers fresh successor creation, simulated legacy-stock migration, historical snapshot/record preservation, changed/custom/derived stock exclusion and idempotence. `test_catalogue_summary.py` reruns048 and checks self-recording/invoker behavior. The prior old-pin browser6 validates historical semantics on a fresh current schema. Those passed checks were not rerun: none starts an actual v0.6.0 database and upgrades it in place with existing pinned evidence. This focused rehearsal fills that gap.

## Rehearsal and evidence

1. Initialized monkey at tagv0.6.0 (`a7538d1`) with migrations through047. Authenticated fixture APIs created accepted scope memberships and a minimal derived precuration; actual UI submit and independent reviewer approval created a curation pinned to original stock methodologyv1. Saved representative LOD2 evidence with points absent. Baseline UI/API checks passed **4/4**.
2. Captured SHA-256 fingerprints of PostgreSQL text/JSON representations:11 existing published-version rows and their snapshots, one curation and one precuration. Captured whole record rows include pins, evidence, stored scores/verdict, workflow state, lock version and timestamps.048/049 were absent from the migration ledger. This proves stored-record/text preservation, not physical disk-page identity.
3. Applied the actual reviewed048/049 files using the migration owner and fail-fast single transactions, without rebuilding the database. Both exited0. All pre-existing captured rows/snapshots stayed byte-identical. Exactly two stock successor publications were added; both migration filenames self-recorded exactly once. Migration assertions passed **6/6**.
4. Restarted API/Vite against the same database using reviewed product06761a7, with server lock fd closed. Upgraded API/UI checks passed **16/16**: old pin/evidence/scores/state unchanged, LOD2 still visible and absent points still blank; both stock schemas expose retainedv1 and successorv2 with expected defaults. A new actual UI precuration review produces a curation pinned tov2. UI mixed AR starts1.5, switching to two-other suggests0.2, segregation starts blank, and new evidence saves through the UI. Normal API connections use app_user; owner access is limited to migrations/fingerprints.
5. Captured the expanded database (13 versions, two curations and two precurations), reran both actual migrations, and compared again. Every captured version/snapshot/record, migration-ledger row and catalogue-view definition/options remained identical. Old baseline fingerprints still match after API/UI use.048 retains security_invoker and the real stored section-score keys. Final fingerprint/idempotence assertions passed **6/6**.

Migration source hashes:

- 048: `0d7510f65d32b5bb566db2a7805207acd6bae577a32dac90afde8e18fa9f068c`
- 049: `084a20f320869f90d44adca4f514e744cd47751d92c8984395ff163e1ef0719c`

Both files were verified byte-identical to Git source06761a7. RHEADf599a600 has no backend/frontend/database difference from that reviewed product. The first attempt to create a new curation directly was correctly refused because its approved precuration was missing; the fixture was completed through actual UI submit/reviewer approval. That guard diagnostic is preserved separately and no product bypass was added.

All screenshots, fingerprint/result JSON, migration logs and helper scripts remain ignored local evidence; no user/auth-state/token table dumps were taken. Only this Markdown report is intended for release documentation. No source changes or new clinical interpretation were introduced. G's next fresh postmerge gate remains a separate required reset/replay.


## Owner-requested shutdown checkpoint

PR449 (G) merged as `121592011fe387e6a83faffe8eaaae543f8ddea5` just before shutdown. Its mandatory fresh postmerge browser gate **has not started and is the first task on resume**. The completed upgrade rehearsal and earlier candidate checks do not substitute for that gate. No new tests or reset were run after the stop request.

Only the owned monkey API/Vite processes were terminated: `kill -TERM 555034 555101`, after verifying their command lines and working directories. `docker stop gc-monkey-db` then stopped the isolated database gracefully (exit0). Verification found no listeners on8052,5190,5455. Dev services were not touched. No OS shutdown command was issued.

The stopped `gc-monkey-db` container and volume `aec87b4e3b288e04fa042f2127ad0b4ac18b2ae42e045fb91abb486f05dcb999` remain present. The volume is mounted at `/var/lib/postgresql/data`; it contains the completed populated-upgrade fixtures and applied048/049. Worktree `/home/bernt-popp/development/gc-wt/monkey` remains detached at reviewed product `06761a7063cf491bd04188608edc30b037d88a84`. All unique upgrade helpers and reusable browser runners are preserved locally under ignored `.planning/wave5-evidence/runner/`; result JSON, screenshots and logs remain ignored, and no authentication-state files were copied.

To inspect the preserved database on resume, use `docker start gc-monkey-db` (do not use monkey `down` or `up` if preserving this database). To run G's required fresh gate, first preserve any desired remaining upgrade evidence, then restore ignored helpers to `/tmp`, clear only stale monkey browser-auth scratch files, sync/fetch master, and run the authorized fresh reset:

```bash
flock /tmp/gene-curator-wave5-gates.lock bash .planning/orchestration/monkey-stack.sh up origin/master 9>&- > /tmp/w5-pr449-reset.log 2>&1
```

Start the API from monkey/backend on8052 using its existing documented `app_user` DATABASE_URL and localhost5190 CORS settings, and start Vite from monkey/frontend with `VITE_API_BASE_URL=http://localhost:8052 VITE_ENABLE_DEV_LOGIN=true node /tmp/w5-baseline-vite-server.mjs 9>&-`. Close fd9 on the API launch too. The retained Vite helper permits exactly the monkey frontend and shared root node_modules path for working fonts. Verify the fresh source contains merge1215920 before recording G results.

With `W5_TEST_PASSWORD` set to the seeded fixture password, the ordered browser commands are:

```bash
node /tmp/w5-baseline-bootstrap-core.cjs
W5_REPORT=/tmp/w5-pr449-core.json node /tmp/w5-baseline-run-all.cjs
node /tmp/w5G-original-bootstrap.cjs
node /tmp/w5J-G-pmid.cjs
node /tmp/w5G-lifecycle-bootstrap.cjs
node /tmp/w5G-lifecycle.cjs
node /tmp/w5-pr440-font-check.cjs
```

Expect core59 plus original G16, lifecycle G7 and font1, but report only actual observed results. The full original G runner already contains readonly→editable checks; `w5G-readonly-continuation.cjs` is a retained five-check diagnostic continuation, not an additional required replay or extra count. Check current standalone-G DOM selectors before interpreting a readonly presentation mismatch with later I; never suppress a product assertion. G's paged precuration fixture helpers also remain available (`w5J-G-paged.cjs`, `w5J-G-paged-recheck.cjs`) if the final merged surface requires that narrow regression. External publication lookup failures must be distinguished from product failures. No J/I/release merge until G's mandatory gate is complete.
