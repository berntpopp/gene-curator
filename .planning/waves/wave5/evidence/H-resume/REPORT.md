# H resumed review and correction

PR443 refreshed cleanly from `fad565a` onto master `7496d36`, merge `c461c10`. Actual Opus5.5 resumed session `a953e0a5-2768-47d9-9517-37a38926b954`, canonical model `claude-opus-5-5`, returned a concrete finding: explicit `is_active:null` was missing from the update guard and could make a PostgreSQL row unreadable after committing it.

A new parameterized API regression failed before the fix with the SQLite NOT NULL IntegrityError. The existing validator now rejects explicit null while preserving omission and false. All eight explicit-null API cases pass. A real app_user PostgreSQL flow creates a schema, updates false, rejects null422, and verifies both GET and unfiltered listing remain readable with false preserved.

Fix `f312c08fef8bbd33f92f12305b61f41488c75442` received actual Opus delta **Verdict: Ship.** (`is_error=false`, same model/session). Full `make ci`, `make check`, and `make diff-cover` passed at this head; backend coverage94.65%, both changed-line reports100%. No generated API types were formatted or modified by this fix. Original uniqueness mapping and derive-store behavior remain scoped to issue432; no216 expansion.

Push hook and narrow browser correction check are recorded separately when completed. This is not a merge or postmerge browser gate. Reviewer JSON is ignored local evidence; no auth tokens or state are copied.

After F444 merged, H cleanly merged master785e573 into `ed6748d8d35f1a9e8e6b34d2747c9006bf2643bd`. Actual Opus integration-only delta again returned **Verdict: Ship** at that exact SHA, same model/session. All H files stayed identical to f312c08. Full `make ci` (including PostgreSQL and diff coverage) passed on ed6748d; push-hook check and browser status follow separately.

Final ed6748d push completed with mandatory pre-push make check passing. GitHub443 verified OPEN/draft at exact ed6748d; worktree clean. Browser correction check still pending its scheduled candidate or postmerge stack.

Final integrated ed6748d metrics: backend94.66%, frontend215 files/2460 tests, backend and frontend changed-line coverage100%. The earlier94.65% figure belongs to f312c08 before the F merge.

After A442 merged, clean integration head `ccd90aa11b5d908cba74ca2ed1ab5012ad3dcfbb` retains all10 H files byte-identical to reviewed ed6748d. No conflict or product edit. Full make ci/check/diff-cover passed on this head, frontend2486 tests, both changed-line coverage100%. Per orchestrator instruction, no extra Opus call for this clean integration of independently reviewed parents. Push hook and narrow candidate browser results follow.

Push at ccd90aa completed with mandatory pre-push make check passing; GitHub443 verified OPEN/draft at the exact head, worktree clean.

Fresh candidate ccd90aa narrow browser passed **10/10**. Actual UI Derive creates one new schema, routes to its editor, uses next patch1.0.1, and leaves source snapshots unchanged; supplementary reads verify latest source scoring configuration copied. Authenticated browser-origin boundary requests accept is_active:false, reject malformed null422, and retain readable false in GET/list. Actual editor reload still works afterward. The expected422 appears in captured browser diagnostics; no other failures. This is candidate evidence, not the later required postmerge gate.
