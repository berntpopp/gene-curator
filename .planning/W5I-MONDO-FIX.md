# W5I saved MONDO label follow-up

Initial actual Opus 5.5 review: SHIP at 62fe62e, with one nonblocking label regression.
Session: 45f7fe7a-786c-4d1b-a793-5acaf635a108.
Review evidence: /tmp/w5-root-I-initial-review.json.

Native fix: 4594ed176f3c5e63f79422b3bd777ad1bb7e43f6. Exact canonical MONDO IDs
bypass the human-disease suggestion filter in the same upstream request. Free text,
partial IDs and trailing-text queries keep the filter. Existing frontend exact-result
matching remains in force: no remapping or stored evidence writes. No migration,
clinical scoring, permissions or RLS change.

Two exact-ID backend regressions failed first. The frontend caller test mounts the
actual DynamicField without diseaseName, checks the returned susceptibility label,
one lookup and no emitted evidence update. All 31 ontology/API backend tests and
14 frontend tests pass. Initial locked full CI at 4594ed1 passed.

Integrated A358ce6c at b9bf5252d48f8886ee43a405586e6151bed26ac5. One test-only
merge conflict was resolved by retaining A's two cancel assertions and the existing
J historical fixture correction. No manual product merge edits. All 97 affected
form/recovery tests pass; final integrated full CI is queued behind the canonical lock.

Mandatory actual Opus delta review is pending until the session-limit reset/new
owner signal. No retry, billing or authentication changes were attempted. Ops has
queued the narrow real-browser stored-ID label check after A/H/E priorities.
No post-fix browser or review success is claimed yet. PR451 remains a draft.

Logs: /tmp/W5I-mondo-red.log, /tmp/W5I-mondo-green-backend.log,
/tmp/W5I-mondo-green-frontend.log, /tmp/W5I-resume-ci.log,
/tmp/W5I-A-targeted.log, /tmp/W5I-integrated-ci.log.
