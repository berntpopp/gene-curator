# H resumed review and correction

PR443 refreshed cleanly from `fad565a` onto master `7496d36`, merge `c461c10`. Actual Opus5.5 resumed session `a953e0a5-2768-47d9-9517-37a38926b954`, canonical model `claude-opus-5-5`, returned a concrete finding: explicit `is_active:null` was missing from the update guard and could make a PostgreSQL row unreadable after committing it.

A new parameterized API regression failed before the fix with the SQLite NOT NULL IntegrityError. The existing validator now rejects explicit null while preserving omission and false. All eight explicit-null API cases pass. A real app_user PostgreSQL flow creates a schema, updates false, rejects null422, and verifies both GET and unfiltered listing remain readable with false preserved.

Fix `f312c08fef8bbd33f92f12305b61f41488c75442` received actual Opus delta **Verdict: Ship.** (`is_error=false`, same model/session). Full `make ci`, `make check`, and `make diff-cover` passed at this head; backend coverage94.65%, both changed-line reports100%. No generated API types were formatted or modified by this fix. Original uniqueness mapping and derive-store behavior remain scoped to issue432; no216 expansion.

Push hook and narrow browser correction check are recorded separately when completed. This is not a merge or postmerge browser gate. Reviewer JSON is ignored local evidence; no auth tokens or state are copied.

After F444 merged, H cleanly merged master785e573 into `ed6748d8d35f1a9e8e6b34d2747c9006bf2643bd`. Actual Opus integration-only delta again returned **Verdict: Ship** at that exact SHA, same model/session. All H files stayed identical to f312c08. Full `make ci` (including PostgreSQL and diff coverage) passed on ed6748d; push-hook check and browser status follow separately.

Final ed6748d push completed with mandatory pre-push make check passing. GitHub443 verified OPEN/draft at exact ed6748d; worktree clean. Browser correction check still pending its scheduled candidate or postmerge stack.

Final integrated ed6748d metrics: backend94.66%, frontend215 files/2460 tests, backend and frontend changed-line coverage100%. The earlier94.65% figure belongs to f312c08 before the F merge.
