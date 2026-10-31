# ClinGen Gene-Disease Validity methodology bundle

`clingen-methodology.json` is the seeded **ClinGen Gene-Disease Validity** pair (SOP v11) as
one import bundle ([docs/METHODOLOGY-IMPORT.md](../../METHODOLOGY-IMPORT.md)): the curation
schema `ClinGen Gene-Disease Validity SOP` (`11.0`), the precuration schema `ClinGen
Precuration` (`SOP v11`) and the pair, as a fresh database has them (049 successor).

The changes to the seeded content: every evidence table gains two columns (#593),
additively; no existing field id is renamed or removed:

| Column | Type | Meaning |
| --- | --- | --- |
| `sources` | `source` | Where the row comes from (VA-Spec `Document`: PMID, DOI, ClinVar, ClinGen allele or validity, URL, database), with GeneFoundry's tool, retrieval date, record hash and citation |
| `direction` | select `supports`, `disputes`, `neutral` | VA-Spec `directionOfEvidenceProvided` |

It also adds a top-level `evidence_summary` (textarea, never scored) and names it as the
synopsis (`ui_configuration.synopsis_field`), shown on the gene page and exported as
`synopsis`.

Importing it as a platform admin publishes the next methodology version of the curation
schema (matched by name and version); the precuration schema is unchanged. Existing
curations keep their pinned version. Export mapping: [docs/EXPORT.md](../../EXPORT.md).
