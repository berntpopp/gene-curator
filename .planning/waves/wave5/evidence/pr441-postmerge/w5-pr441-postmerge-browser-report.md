# PR 441 postmerge browser gate

Fresh isolated stack at exact merged master `7496d3663e68b91c53263337d4ee0c936f176b49`: core **59/59**, narrow review **27/27**, font check **1/1**. Zero fatal errors. PostgreSQL 5455, API 8052, Vite 5190; no development-stack interaction.

Actual Chromium UI exercised pending membership denial/acceptance, curator save/reload, precuration submit and independent approval, curation request changes/revision/resubmission, two independent approvals, viewer read-only behavior, full re-curation with replacement activation and original archive, and administrator author self-approval denial. The former #430 repeat-approval assertion passes.

Narrow: after Bob approves once, Approve is absent while Request changes remains available and succeeds through UI. Browser-origin authenticated comment creation and resolution pass. Resubmission resets the vote. Three legacy reviewer assignments with two submitted approvals leave an in-review item with zero additional approvals needed; the already-approved reviewer sees an enabled Approve action and activates through UI. The two checks beyond the candidate 25 are fresh reviewer invitation setup.

Coverage boundaries: fixture creation/readback uses API; primary lifecycle transitions use UI. The legacy review-submit API is deliberately exercised for that compatibility edge. Comment capability uses browser-origin authenticated API because the already-approved empty diff has no composer; no UI composer claim. Valid isolated derived schemas test workflow, not clinical scores/defaults. Published methodology versions remain unchanged.

IBM Plex Sans actually loaded, verified through document.fonts. The scratch Vite server allows only the monkey frontend and exact shared dependency directory. Known non-admin dashboard members403 and occasional Vuetify scroll warning remain baseline observations. No new fatal errors or failed assertions. Candidate harness correction and original baseline failure remain separately preserved in their directories.
