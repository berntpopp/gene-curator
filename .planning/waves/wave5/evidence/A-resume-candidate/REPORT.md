# A resumed review correction: candidate browser checks

Fresh isolated candidate `9e04844515da90e5fe08b11cb92bab9d3b8007b3`, containing correction5237618 and master785e573. New narrow Chromium checks passed **36/36**: precuration13/13, curation13/13, delayed-save cancellation10/10.

Two-tab precuration and curation flows created actual local edits, submitted in the other tab, reloaded readonly, and confirmed authoritative server evidence plus no editable recovery prompt. Escape followed by the actual Discard confirmation preserved each hidden local snapshot. An independent reviewer requested changes through the UI, after which the author restored, saved and reloaded the preserved draft.

For each form, the browser held a real save response after its server write, typed more changes, confirmed Cancel/Discard, then released the response. Neither delayed response recreated a recovery snapshot. Reopening showed the server-saved value and no recovery prompt; later discarded typing stayed discarded.

An initial keyboard harness targeted the page heading outside the form, so Escape could not reach the form handler. The failed harness result is retained separately. Focusing the actual form tab before Escape exercised the correct user keyboard path; no product fix was needed.

These are candidate checks, not the required fresh postmerge gate. Local JSON/screenshots are ignored, and no auth-state files/tokens were copied. New scratch helpers are `/tmp/w5a-precuration-readonly.cjs`, `/tmp/w5a-expanded-curation.cjs`, and `/tmp/w5a-late-save-cancel.cjs`.

Existing recovery-flow replay also passed **23/23** on this candidate: another-tab snapshot preservation, newer server choice, explicit stale restoration with fresh lock, actual409 and reload recovery, revert cleanup, empty saved values. This replay was warranted because the correction changes markSaved cancellation behavior.
