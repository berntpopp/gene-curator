# W5R legacy duplicate cleanup

Actual independent Opus5.5 reviewed release head453a49b/product320a338 and returned
SHIP in sessionb09f17b0-07b0-4e07-bb88-b14dedb9c10b. It explicitly covered the manual
schema-validator, review-guard and EvidenceTableField integrations in the existing
integration ledger. Local result: /tmp/w5-root-R-opus-integration-20261022/result.json.
It did not independently run CI/browser gates or make new clinical judgments.

One nonblocking wording finding identified a second tracked copy of the old downloader
and raw documents in legacy plan/scripts. The owner’s helper-cleanup request covers
these duplicates; root explicitly assigned their audit and precise untracking.

The seven files are byte-identical to their already-untracked pre-GSD counterparts:
plan/scripts/download_clingen_docs.py, requirements.txt, downloads/gimjournal_article.html
and the four PDFs under downloads/pdfs. No maintained caller was found: tracked references
to the helper/cache are confined to its README and ignore rules. Eight Markdown documents,
indexes and source citations remain tracked. The legacy README now describes local-only
raw files instead of advertising installation/execution of the retired helper.

Only three exact rooted ignore entries were added: the helper, its dependency file and
its dedicated downloads directory. No blanket extension rule. All seven local files remain
byte-for-byte unchanged (7,951,846 bytes total). Ignore probes over860 tracked application,
test, config and maintained script files matched zero. All modified Markdown links resolve.
No product code, current dependency lockfile, migration, clinical evidence or historical
scoring expectation changed. The previous eight-file pre-GSD cleanup remains separate;
this seven-file duplicate cleanup brings the release-candidate archival untracking to15.
Current master retains tracked copies until release integration; local root files are not
removed or altered by this worktree’s index cleanup.

This new cleanup delta still needs actual Opus re-review together with final release facts.
Existing product CI/browser evidence remains attributable to unchanged source320a338.
No publication or approval bypass is implied by this documentation-only cleanup.
