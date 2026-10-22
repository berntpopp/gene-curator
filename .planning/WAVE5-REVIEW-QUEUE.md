# Required Opus review queue

Every entry requires actual Claude Code Opus5.5 using ponytail:ponytail-review.
Account monthly spend cap currently prevents it; do not substitute native approval.
Review the latest pushed head and reconcile merge-only parent changes. Fix rounds
review only the task delta plus connected behavior, not every already-reviewed line.
No unreviewed draft becomes ready or merges. Actual SOPv11 PDF required for clinical work.

| PR | Last substantive head | Required review |
| --- | --- | --- |
|442 recovery|6cdc7ee718012470fa343db02ce446b8b3f841ec (readonly follow-up after528822c)|Delta from c1dca8d; prior reviewer session98bfc166-0239-48b0-9f23-92815e8a7bd9; review2 produced no verdict; include readonly restore guard/browserfinding|
|443 derive|fad565a3b55f21d826b27060bc86775c0510ec19|Delta from95e7991 (same task patch as reviewed e227caf); prior sessiona953e0a5-2768-47d9-9517-37a38926b954; review2 no verdict|
|444 robustness|59689248c81d0b5eccc9d21941af99688551420c|Delta from38df48d (same patch as reviewed0ff7c982); prior sessionef53a327-7c16-49b2-b434-d0d0608a854d; all five findings addressed|
|445 conditions|4e7cf15519d51d2c8360895141756df9e88cb2d4|Initial full task review; actual app_user entry paths, condition parity, no ACTIVE exception; declared-default initialization follow-up with readonly/value preservation|
|446 score trace|01e85d7abd3ffe82adb3c40365a1d73a1c9aabbc|Initial E-only review after parent tasks, including exact classification metadata, stale previews, deletion of client arithmetic|
|449 PMID/workflow|cdc199c6f937022b590ccbb7663a0eeb071c3c42|Initial full task review; network before locks/autoflush, exact refreshed snapshot and permission checks, serial DB operations in bulk|
|450 immutable successor|6fbddc40c99ad416b873754b04f3d11f0017d42f|Initial full task review plus actual SOPv11 PDF; new version only, existing snapshots/pins/evidence invariant, legacy explicit-points containment|
|451 UI polish|62fe62e (includes D/J browser fixes)|Initial full task review; actual browser timings/readonly/contrast/scroll/ontology suggestion limits|

|452 release preparation|0bebdb9a1522f5125f08a0ac445d6727ae253d0a (plus report-link follow-up)|Initial release-only Opus ponytail review; PR-cited release notes, immutable upgrade guidance, all active versions, sanitized report/runner provenance; parent functional reviews remain required|

Completed:440 actual Opus SHIP atfdc745e;441 actual Opus delta SHIP atc51ad81,
sessionf5ce24c1-8b30-4d37-9039-f4c8ebd70e00. Both merged with local/GitHub CI and
fresh browser evidence. Do not rereview them absent new changes.

Stored CLI results live under /tmp/w5-W5?-review?.json; do not treat tool errors or
partial responses as SHIP. Preserve accurate native versus Opus implementation/review
provenance in reports. Before merge, update against current master, rerun required
local gates, push, check behind=0, then pipefail merge.sh; independently verify MERGED.
