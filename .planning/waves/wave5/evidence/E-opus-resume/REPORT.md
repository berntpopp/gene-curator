# E resumed independent review

PR446: actual Claude Code claude-opus-5-5, is_error=false.
Session: `05a8493c-5865-449e-b94e-01ead94c8a8f`. Read-only review; no new tests were run by reviewer.

**Verdict: FIX** at `01e85d7abd3ffe82adb3c40365a1d73a1c9aabbc` (E-only review)

**What this change does:** The backend trace now records which classification rule was picked (`point_model.py:188`). On the frontend, one `ScoreTrace` component replaces the live, workspace, form-summary and saved-detail score views. It renders only the numbers the backend returns, with no thresholds, `/ 18` totals or legacy models/rescue caps worked out in the browser. `useSchemaScoring` is deleted, and every edit now clears the old preview straight away.

**Must fix**

1. **The score panel disappears and the layout jumps on every keystroke** (`DynamicForm.vue:250-255`, `SchemaDrivenCurationForm.vue:376`, `CurationFormView.vue:107,265`)
   - **What happens:** Each keystroke runs `scheduleValidate`, which calls `clearValidationResult('form')`. That sends `validation-change(undefined)`, so `scoreSnapshot(undefined)` returns `null` and `frame.score` becomes `null`. Then `showPanel` turns false and the whole `<aside>` unmounts. That aside also holds the "Before you submit" checklist.
   - **User impact:** On wide screens the grid switches from `1fr 340px` to `1fr` and back about 500 ms after typing stops, plus the request time. The text being typed reflows under the cursor, and the checklist blinks out. Before E, the old snapshot stayed until a reply came back. The Flows spec asserts `frame.score` is `null` after `undefined`, so this is deliberate, but the layout effect is not tested.
   - **Same cause in the other live view:** In the `ScoreDisplay` sidebar during the 500 ms debounce, `validating` is still false, so `ScoreTrace.vue:296` shows "Unavailable points / Score breakdown unavailable for this record". That reads as a permanent fact while it is really just pending.
   - **Smallest fix:** Keep showing the old numbers' container but not the numbers:
     - Leave the aside mounted once a score has been shown, and render a skeleton while `score` is `null`.
     - In DynamicForm, add a `pending` ref. Set it in `scheduleValidate`, clear it in `validateForm`'s `finally` when the result was not superseded, and pass `:loading="validating || pending"`.
   - **Regression tests:**
     - CurationFormView: after `setScore(null)` following a score, `.ws-panel` still exists and shows a skeleton.
     - ScoreDisplay/DynamicForm: during the debounce the skeleton shows, not "unavailable for this record".

**Verified OK (no finding)**
- **Exact rule:** `classify` returns a copy of the matching override or band, and that copy goes into the trace. The parametrised unit test checks it equals `classify(...)` for band, `requires` and fallback cases. The UI shows `min`, `requires`, `when/field/in` and `description` as given and does not invent a verdict. Traces saved before E show "Classification rule details were not stored."
- **Custom caps:** section, category and total caps come from the trace. `capText` only compares `raw > cap`, and a missing cap shows "—". The detail spec checks the pinned cap of 2 and no `/ 6`.
- **Preview / saved / detail parity:** the Postgres test runs as `app_user`. For both the old-pin and new rows it checks preview trace = saved trace = detail trace. I did not re-run it; I relied on your report.
- **Unmapped and out-of-range paths:** still reported through `clingen.py:261` as validation warnings, which `DynamicForm` shows. E does not change them.
- **Stale-reply protection:** `clearValidationResult` increments the request counter, and the store spec covers a reply arriving after the clear.
- **Qualitative and no-trace data:** the backend's numeric `total_score` and `verdict` are shown as returned, with "breakdown unavailable" and no invented trace or cap. One note: `scorePreview.spec` "keeps qualitative totals unavailable" uses `{verdict}` only, but the real qualitative engine does return a number. The display is still truthful.

**Not blocking, record honestly**
- **#386 is still open:** the preview shows StrongAssociation/10 with no trace, while the saved row shows no_known/0 with a ClinGen trace, rule `no_known` and cap 18. E now displays that misleading saved trace more prominently. It is the excluded dispatch bug, so there is no qualitative save parity, and browser flows 25/26 inherit the baseline failure. Do not call that run a complete pass.
- **Submit gating during the debounce:** `isValid` is now `true` while a check is pending, where before it held the old result. Backend save and submit validation remains the real guard.
- **Recompute backfill:** the next `recompute_scores` run sees every row as changed, because the trace gained `classification_rule`. It rewrites them without an audit log line, since total and class are unchanged. That is fine, and a second run is idempotent.
- **Issues:** #429/#266 are not done until this merges. #264 must not be closed while this is a draft, and the accepted #268 cuts stay listed as non-goals.

I did not run any gates or browser checks; this is a read-only review. I did not re-review parent F/A/D or clinical bands, since E changes no numbers. Finding 1 is from reading the code, not from seeing it in a browser.

Raw JSON is retained locally and ignored. Findings require reproduction, scoped fixes, actual Opus delta review, and relevant browser recheck before merge.
