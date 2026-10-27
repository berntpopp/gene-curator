# PR446 fresh postmerge browser gate

Fresh origin/master at `182a66a1179faf845fed8f3627eb16ee0c87c401`, isolated Postgres5455/API8052/Vite5190. Canonical core passed **59/59**: every role, invitation restrictions, untouched declared-false defaults, two review rounds, independent approvals, re-curation and D1. No failed assertions or fatal prerequisites.

E timing/layout narrow passed **17/17**. Actual UI edits preserve the same score-aside DOM node and width, keep the submit checklist visible, remove old numeric trace immediately, and show a skeleton throughout debounce and network delay. Real backend preview responses are held and released by the browser harness; a superseded response cannot restore old numbers or end the pending state, and the newest response restores the current trace.

One deliberately mocked503 response verifies pending terminates with explicit unavailable-score text while the checklist remains. That503 appears as an expected browser diagnostic. The other delayed responses come from the real backend; the run does not present the mocked error as a real service outage. Authenticated API fixture creation/read-back is distinguished from actual UI editing and response-timing checks.

Loaded-font check passed **1/1**: IBM Plex Sans. This is fresh postmerge evidence, independent of prior R candidate results. Existing excluded#386 qualitative preview/save mismatch was not expanded, fixed or claimed passing. JSON/screenshots/helpers remain ignored local evidence; no auth-state/token files copied. No product changes or duplicate passed tests were introduced.
