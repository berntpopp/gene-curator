# MCP study round 5 (Claude Code, master 952c6bee, /mcp core 78 tools)

21/24 success (R4 24/24), 0 unsafe, $5.66. Stop rule NOT met. All 3 failures are T7 (founding paper missing; R4 counted that as a pass). Second independent grader used for T7/T8.

| Task | OK (R4) | Wall s | Calls | In/out tok | $ | Overall |
|---|---|---|---|---|---|---|
| T0 | 2/2 | 17 | 2 | 24k/1.4k | .16 | 9 |
| T1 | 2/2 | 28 | 7.5 | 70k/2.5k | .27 | 8 |
| T2 | 2/2 | 35 | 7 | 93k/2.8k | .32 | 8 |
| T2b | 2/2 | 59 | 11.5 | 183k/4.8k | .54 | 8 |
| T3 | 2/2 | 28 | 3 | 50k/2.1k | .24 | 8.5 |
| T4 | 2/2 | 26 | 5 | 54k/1.9k | .22 | 7.5 |
| T5a / T5b | 2/2, 2/2 | 21 / 24 | 2 / 2.5 | 40k, 31k | .20 / .23 | 8 / 7.5 |
| T6 | 2/2 | 27 | 5 | 54k/2.1k | .24 | 8 |
| T7 SLC12A3 | 0/3 (3/3) | 131 | 38 | 701k/13.7k | 2.71 | 8 |
| T8 NPHS1 | 3/3 | 41 | 5 | 79k/3.7k | .52 | 8 |

Token targets: median input/task 61.6k over runs, 54.1k over task medians (<=55k); T2 93k met; T2b 183k missed (<=140k); tool-list share 20.9% with re-reads, 34% incl. tool-search schemas (<=15% missed); largest result 8,053 B get_curation_schema (met); curator tools 78 (met).

Median ratings vs R4: discoverability 8 (0), speed 9 (0), token efficiency 7 (0), error clarity 7.5 (-0.5, n=2), correctness/safety 9 (+0.5), overall 8 (0). Primary flows: 8/8/7/7.5/9/8.

T7 (both graders, fail 3/3): correct MONDO:0009904, AR, real on-topic PMIDs, within caps, classification consistent, nothing fabricated. Every run read Simon 1996 (PMID 8528245) and cohort papers but excluded them because abstracts lack per-patient genotypes -> 4-6.8 genetic points, Moderate/Limited vs reference Definitive. Minor: null+other probands filed as other_variant_type; T7-4 duplicate proband row; T7-1 0.5-point upgrades without functional evidence.
T8 (both graders, pass 3/3): all three planted errors caught, changes requested.

## Findings (impact x frequency)
1. (3, 3/3) Abstract-only literature caps T7: add per-paper genotype extraction (PubTator variant annotations or PMC full text) to get_publication.
2. (2) Literature calls drive cost: get_publication takes a list of PMIDs; search_pubmed gene filter on title/abstract only; flag papers whose abstract contains variants.
3. (2) Warnings: validate PMIDs found in free text; drop the free-text-PMID warning on evidence_summary (fired on 4/5, ignored); misfiled-patient check also on model rows mentioning proband/patient.
4. (2, 5/24) get_curation_schema(path=) without the envelope, with point ranges.
5. (1) Review read and get_curation: warnings once, sentence-level diff, score trace opt-in; check /curations/{id}/review missing previous reviews after request changes.

## Study artefacts
T7-2/T7-3/T8-2/T8-3 void (parallel seeding collided on gene creation), rerun as runs 4/5 sequentially. T7 now requires the founding paper (not comparable to R4). T8 fake PMID planted in text. Error clarity n=2. GeneFoundry unreachable; T7 reference from the stack's own lookups. PATs revoked.
