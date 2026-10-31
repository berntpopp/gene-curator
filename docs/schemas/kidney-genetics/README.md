# Kidney Genetics (KGDB) methodology bundle

`kgdb-methodology.json` is the kidney-genetics-db curation methodology (alpha, draft
iteration 3; see [kidney-genetics-db#439](https://github.com/berntpopp/kidney-genetics-db/issues/439))
as one import bundle ([docs/METHODOLOGY-IMPORT.md](../../METHODOLOGY-IMPORT.md)):

| Object | Name | Version |
| --- | --- | --- |
| Precuration schema | `KGDB Mendelian Precuration` | `alpha` |
| Precuration schema | `KGDB Susceptibility Precuration` | `alpha` |
| Curation schema | `KGDB Mendelian Curation` (point model) | `alpha` |
| Curation schema | `KGDB Susceptibility Curation` (Established / Likely / Uncertain / Refuted; approved by KGDB on 2026-10-31, [kidney-genetics-db#473](https://github.com/berntpopp/kidney-genetics-db/issues/473)) | `alpha` |
| Workflow pair | `KGDB Mendelian` (default of scope `kidney-genetics`) | `alpha` |
| Workflow pair | `KGDB Susceptibility` | `alpha` |

The curator picks the pair by hand: a Mendelian entity is precurated with the Mendelian
precuration schema, a susceptibility (risk allele) entity with the susceptibility one. Each
precuration schema belongs to one pair, so approval opens the curation of the right pair
without routing code. `relationship_type` is fixed per precuration schema and becomes part of
the entity key (`MONDO|MOI|SUSCEPTIBILITY`).

## Import

Platform admins only. The import is idempotent: the same file again changes nothing; changed
content publishes the next methodology version, and existing curations keep theirs. A changed
schema `description` is written without a new version. Every
schema runs the publish gate, including the scoring tests embedded below.

- **UI:** Schema Management, *Import methodology*, with a dry run first.
- **REST:**
  ```bash
  curl -X POST "$API/api/v1/schemas/methodologies/import?dry_run=true" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data @docs/schemas/kidney-genetics/kgdb-methodology.json
  ```
  then the same call without `dry_run`.
- **MCP:** `import_methodology` on `/mcp/full` (not on core `/mcp`).

`scope_default` makes `KGDB Mendelian` the default pair of the seeded `kidney-genetics` scope.
Remove it from the file to import without touching a scope.

## Scoring

Mendelian (`scoring_configuration.point_model`, engine `point_model`; see
[docs/POINT-MODEL.md](../../POINT-MODEL.md)):

| Category | Row | Default | Cap |
| --- | --- | --- | --- |
| `genetic.probands` | unrelated proband with a real variant (`require_variant`) | 1, de novo confirmed 1.5 | 10 |
| `genetic.segregation` | one row, summed LOD 2 / 3 / 5 | 1 / 2 / 3 (`rule: step`) | 3 |
| `genetic.cohort` | significant case-control or burden study | 2 | 4 |
| `experimental.models` | model with a matching phenotype | 2, partial mechanism fit or morpholino only 1 | 4 |
| `experimental.functional` | assay or rescue | 1 | 2 |

Genetic cap 12, experimental cap 6, total 18; a proband row scores at most 1.5. A proband row
scores 0 when `variant_source` is `not_given`, `duplicate_of` is set, `zygosity` is blank, a
compound heterozygote has `phase` `unknown` or blank (only confirmed or suspected in trans
count), or `allele_frequency` is above 2.5e-3, or above 1e-4 when `zygosity` is
`heterozygous` or `hemizygous`. The AF cutoff keys on the row's zygosity, not on the entity's
MOI: an AD row must be entered as heterozygous (or hemizygous for XL) to get the 1e-4 cutoff.
At most 2 points per recurrent variant (`group_by: variant`); rows are grouped by the variant
text after trimming and case folding only, so `c.100C>T` and `NM_006580.4:c.100C>T` are two
variants (not HGVS-normalised). A row without a PMID scores nothing.

Bands, first match wins: Definitive >= 12 and `replicated_over_time`; Strong >= 12; Moderate
>= 7; Limited > 0; No Known 0. Definitive, Strong and Moderate also need genetic >= 4
(`section_min`). Contradictory evidence with impact `refuted` or `disputed` sets that class.
Reviewer flags: total within 2 points of a band edge, experimental above genetic, hotspot
(the top 2 variants carry >= 50% of proband points and one of them is in 2 or more scoring
probands; single-proband variants never raise it; the hotspot pilot case raises it).

Susceptibility (approved by KGDB in
[kidney-genetics-db#473](https://github.com/berntpopp/kidney-genetics-db/issues/473); ClinGen
LP/RA WG tiers, Schmidt 2024, PMID 38054408, put into point-model form). One entity is gene +
disease + one named risk allele, haplotype or genotype; studies of different alleles do not add up.

| Category | Row | Default | Cap |
| --- | --- | --- | --- |
| `association.studies` | significant study of the named allele, OR and 95% CI oriented to it | 1; 2 if >= 50 cases and >= 50 controls; 3 if >= 500 and >= 500 or `design` `meta_analysis` | 9 |
| `experimental.functional` | assay, expression/eQTL or model supporting the allele | 1 | 2 |

Total 11. A study row scores 0 when `significant_after_correction` is false or blank,
`included_in` names a meta-analysis row (so a cohort is not counted twice), or
`effect_direction` is `protective` (protective alleles are recorded, not scored). Effect size is
recorded, not scored (`p_value` is stored only; a blank one does not change the points); an OR
< 1 for the curated risk allele is contradictory evidence. The size tier is only the default: the
form accepts any entered value from 0 to 3 (e.g. fewer for bias or poor ancestry matching), and
an entered value stands. The reviewer must check, in the score trace, any entered value above the
row's size tier.

Bands use the association section only, so functional data never move the class: Established
>= 6 and `meets_very_strong` (ClinGen Very Strong: > 1000 individuals, extensive replication,
little inconsistency, bias excluded); Likely >= 4; otherwise Uncertain. A curation with 0
association points also falls back to Uncertain; KGDB does not publish it (open question Q3 of kidney-genetics-db#473).
`replicated_over_time` is kept (frozen id) but no longer sets a susceptibility class.
Contradictory evidence with impact `refuted` sets `refuted` (Refuted association); `disputed`
sets Uncertain, because ClinGen puts conflicting risk-allele evidence under Uncertain. The trace's
`classification_rule` names the override.

Embedded `scoring_configuration.tests` (run at every publish and import):

| Test | Total | Class |
| --- | --- | --- |
| CLDN16 (AR HOMG3): 10 probands, 6 experimental, replicated | 16 | definitive |
| NEK8 (AD ADPKD): 12 genetic, 2 experimental, not replicated | 14 | strong |
| SIX5 (AD BOR): disputed by contradictory evidence | 1 | disputed |
| DNAJB11-like: genetic 2 + experimental 6 | 8 | limited (not moderate: genetic < 4) |
| Hotspot: 6 probands, one recurrent variant | 2 | limited |
| Compound het without a phase | 1 | limited |
| Proband without zygosity (AF cutoff) | 1 | limited |
| Row rules (de novo, zero rules, AF caps, models 1) | 4.5 | limited |
| Susceptibility: established (two 600/700 studies, Very Strong) | 6 | established |
| Susceptibility: likely (600/700 + 120/150, not Very Strong) | 5 | likely |
| Susceptibility: small study; not significant after correction, or blank, scores 0 | 1 | uncertain |
| Susceptibility: refuted overrides an established score | 6 | refuted |
| Susceptibility: meta-analysis, its included cohorts not counted again | 3 | uncertain |
| Susceptibility: protective study recorded, not scored | 0 | uncertain |
| Susceptibility: functional only | 2 | uncertain |
| Susceptibility: three 600/700 studies, not Very Strong | 9 | likely |
| Susceptibility: one 600/700 study + two functional rows (`section_min`) | 5 | uncertain |
| Susceptibility: disputed overrides an established score | 6 | uncertain |
| Susceptibility: blank p value, significant after correction, scores by size | 2 | uncertain |
| Susceptibility: Very Strong, 5 association + 2 functional (`section_min`) | 7 | likely |

## LLM sharing

Evidence facts KGDB agents need (variant class and source, phase, allele frequency, LOD,
model genotype and phenotype, assays, the diagnostics section, unscored reports and context)
carry `llm_share: true`. `variant`, `zygosity`, `de_novo`, `p_value`, `odds_ratio`, `pmid` and
`description` are shared by default (seeded evidence keys). Judgement keys (`points`, `impact`, `replicated_over_time`,
`evidence_summary`, `explanation`) never do; the server refuses them.

## Mapping to the curation export

KGDB imports from `GET /api/v1/export/curations?scope_name=kidney-genetics`
([docs/EXPORT.md](../../EXPORT.md)) with a scope member's token (otherwise `evidence` and
`methodology.version` are null).

| KGDB | Export field |
| --- | --- |
| Gene | `hgnc_id`, `approved_symbol` |
| Gene_Entity_ID / match key | `entity_key` (opaque), with `mondo_id`, `moi_hpo_id`, `relationship_type` |
| Disease | `disease_name`, `mondo_id` |
| Class | `final_classification` (reviewer-approved), `computed_verdict` (point model) |
| Points | `total_score`, `genetic_score`, `experimental_score` (`genetic_total`, `experimental_total`); trace in `scores` |
| Methodology | `methodology.schema_name`, `methodology.version`, `methodology.version_id` |
| Curator, reviewer | `curator_name`, `reviewer_name`, `approved_at`, `activated_at` |
| Provenance link | `url`, `curation_id` |
| Retraction | `status` `archived`, `archived_at`, `archive_reason` |
| Evidence rows | `evidence.genetic.*`, `evidence.experimental.*`, `evidence.contradictory_evidence` |
| Susceptibility rows | `evidence.association.studies` |
| Clinical diagnostics | `evidence.diagnostics` (see below) |
| Diagnostics notes | `evidence.diagnostics_notes.transcript_verified_via`, `.detectability_note` (not in KGDB's `Diagnostics`) |
| PMIDs | `pmids` |

Class keys: `definitive`, `strong`, `moderate`, `limited`, `no_known`, `disputed`,
`refuted` (KGDB `Definitive` ... `No Known Disease Relationship`); susceptibility
`established`, `likely`, `uncertain`, `refuted` (KGDB `Established association`, `Likely
association`, `Uncertain association`, `Refuted association`).

### Diagnostics: GC evidence -> KGDB `Diagnostics`

`evidence.diagnostics` uses the keys and enums of KGDB's `Diagnostics` schema
(`backend/app/schemas/gene_disease_association.py`, `extra="forbid"`). Evidence-table cells
hold text or lists of text, never objects, so two parts are flat in GC and the importer
must reshape them exactly like this; everything else passes through unchanged:

| GC | KGDB |
| --- | --- |
| `recommended_transcript` with every key blank | `recommended_transcript: null` |
| `recommended_transcript.mane_status` blank (KGDB requires it) | `mane_status: "not_checked"` |
| `recommended_transcript.{refseq, ensembl, mane_status, legacy_transcript, numbering_conversion}` | same keys |
| `detectability[].{challenge, share_of_variants, affected_variants, methods, negative_report_does_not_exclude, sources}` | same keys |
| `detectability[].tools[]`: text `name \| url \| pmid_or_doi`, split on ` \| `, empty parts null | `tools[]`: `{name, url, pmid_or_doi}` |
| `resources[].{type, name, url, language, audiences, maintainer, conflict_of_interest}` | same keys; `type` is `patient_organisation`, `registry`, `variant_database`, `guideline` or `other` |
| `resources[].verified_method`, `resources[].verified_date` | `resources[].verified`: `{method, date}` |
| `diagnostics_notes.transcript_verified_via`, `diagnostics_notes.detectability_note` | no KGDB key yet (kept outside `diagnostics`) |

Drop blank optional keys (null or `""`) before validating. KGDB's text limits are set as `max_length`
on the fields (`legacy_transcript` <= 50, `numbering_conversion` <= 500, `share_of_variants`
<= 100, `affected_variants` <= 300, resource `name` 1-200, `language` <= 20, `maintainer` <=
200, `conflict_of_interest` <= 500); the server does not check evidence-table cells, so the
importer checks them too. Importer-only limits: resource `url` <= 2000, `methods` <= 20 entries of <= 50
characters, `tools` <= 10 entries with a non-empty name <= 100 (drop an entry whose name part
is blank), `pmid_or_doi` <= 100, `sources` <= 10 entries of <= 300, `audiences` <= 10 entries
of <= 50, at most 20 detectability rows and 50 resources; `challenge` (<= 300) is one of the
GC select values. RefSeq (`^NM_\d+\.\d+$`) and Ensembl (`^ENST\d{11}\.\d+$`) formats are
checked by GC. Open KGDB questions: the curator
brief also asks for a transcript `verified_via`, a `detectability_note` and a resource
`country_or_scope`, which KGDB's `Diagnostics` forbids; the first two are kept outside
`diagnostics`, `country_or_scope` is left out until KGDB adds it.

## Frozen field ids (the KGDB import contract)

These ids are the data keys of `evidence_data` (curations) and the precuration's evidence;
`[]` marks an evidence table row. Do not rename or remove one: add a new id and deprecate the
old one in a new methodology version, and tell KGDB first. `backend/tests/unit/test_kgdb_methodology.py`
fails when this list and the bundle differ.

### KGDB Mendelian Precuration

```text
clingen_curated
clingen_url
clingen_classification
mondo_id
disease_name
mode_of_inheritance
relationship_type
omim_id
orphanet_id
lumping_splitting_applicable
lumping_splitting_decision
lumping_splitting_rationale
replaced_mondo_id
binning
mechanism
kidney_relevance
cakut_subtype
clinvar_plp_count
genereviews_url
prefill_notes
curator_notes
```

### KGDB Susceptibility Precuration

```text
clingen_curated
clingen_url
clingen_classification
mondo_id
disease_name
mode_of_inheritance
relationship_type
omim_id
orphanet_id
lumping_splitting_applicable
lumping_splitting_decision
lumping_splitting_rationale
replaced_mondo_id
binning
mechanism
kidney_relevance
cakut_subtype
clinvar_plp_count
genereviews_url
prefill_notes
curator_notes
```

### KGDB Mendelian Curation

```text
genetic
genetic.probands
genetic.probands[].proband_label
genetic.probands[].variant
genetic.probands[].variant_class
genetic.probands[].zygosity
genetic.probands[].phase
genetic.probands[].de_novo
genetic.probands[].variant_source
genetic.probands[].allele_frequency
genetic.probands[].duplicate_of
genetic.probands[].pmid
genetic.probands[].points
genetic.probands[].explanation
genetic.segregation
genetic.segregation[].families
genetic.segregation[].summed_lod
genetic.segregation[].method_note
genetic.segregation[].pmid
genetic.cohort
genetic.cohort[].study_label
genetic.cohort[].cases_with_variant
genetic.cohort[].cases_total
genetic.cohort[].controls_with_variant
genetic.cohort[].controls_total
genetic.cohort[].odds_ratio
genetic.cohort[].p_value
genetic.cohort[].pmid
genetic.cohort[].points
experimental
experimental.models
experimental.models[].organism
experimental.models[].genotype
experimental.models[].phenotype
experimental.models[].mechanism_fit
experimental.models[].morpholino_only
experimental.models[].pmid
experimental.models[].points
experimental.functional
experimental.functional[].assay
experimental.functional[].finding
experimental.functional[].pmid
experimental.functional[].points
contradictory_evidence
contradictory_evidence[].description
contradictory_evidence[].impact
contradictory_evidence[].source
contradictory_evidence[].pmid
replicated_over_time
reported_not_scored
context_notes
evidence_summary
diagnostics_notes
diagnostics_notes.transcript_verified_via
diagnostics_notes.detectability_note
diagnostics
diagnostics.recommended_transcript
diagnostics.recommended_transcript.refseq
diagnostics.recommended_transcript.ensembl
diagnostics.recommended_transcript.mane_status
diagnostics.recommended_transcript.legacy_transcript
diagnostics.recommended_transcript.numbering_conversion
diagnostics.detectability
diagnostics.detectability[].challenge
diagnostics.detectability[].share_of_variants
diagnostics.detectability[].affected_variants
diagnostics.detectability[].methods
diagnostics.detectability[].tools
diagnostics.detectability[].negative_report_does_not_exclude
diagnostics.detectability[].sources
diagnostics.resources
diagnostics.resources[].type
diagnostics.resources[].name
diagnostics.resources[].url
diagnostics.resources[].language
diagnostics.resources[].audiences
diagnostics.resources[].maintainer
diagnostics.resources[].conflict_of_interest
diagnostics.resources[].verified_method
diagnostics.resources[].verified_date
```

### KGDB Susceptibility Curation

```text
association
association.studies
association.studies[].study_label
association.studies[].design
association.studies[].variant
association.studies[].ancestry
association.studies[].cases_total
association.studies[].controls_total
association.studies[].odds_ratio
association.studies[].p_value
association.studies[].pmid
association.studies[].significant_after_correction
association.studies[].effect_direction
association.studies[].included_in
association.studies[].points
experimental
experimental.functional
experimental.functional[].assay
experimental.functional[].finding
experimental.functional[].pmid
experimental.functional[].points
contradictory_evidence
contradictory_evidence[].description
contradictory_evidence[].impact
contradictory_evidence[].source
contradictory_evidence[].pmid
meets_very_strong
replicated_over_time
reported_not_scored
context_notes
evidence_summary
diagnostics_notes
diagnostics_notes.transcript_verified_via
diagnostics_notes.detectability_note
diagnostics
diagnostics.recommended_transcript
diagnostics.recommended_transcript.refseq
diagnostics.recommended_transcript.ensembl
diagnostics.recommended_transcript.mane_status
diagnostics.recommended_transcript.legacy_transcript
diagnostics.recommended_transcript.numbering_conversion
diagnostics.detectability
diagnostics.detectability[].challenge
diagnostics.detectability[].share_of_variants
diagnostics.detectability[].affected_variants
diagnostics.detectability[].methods
diagnostics.detectability[].tools
diagnostics.detectability[].negative_report_does_not_exclude
diagnostics.detectability[].sources
diagnostics.resources
diagnostics.resources[].type
diagnostics.resources[].name
diagnostics.resources[].url
diagnostics.resources[].language
diagnostics.resources[].audiences
diagnostics.resources[].maintainer
diagnostics.resources[].conflict_of_interest
diagnostics.resources[].verified_method
diagnostics.resources[].verified_date
```
