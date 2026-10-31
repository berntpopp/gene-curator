# Curation export v1

A read-only feed of reviewed curations for downstream publishers (for example
kidney-genetics-db). Gene Curator stays the source of record; consumers sync from this feed.

```
GET /api/v1/export/curations?scope_name=kidney-genetics&updated_since=2026-01-01T00:00:00Z
```

The response schema is `CurationExportPage` in the OpenAPI document (`/openapi.json`); pin it
and drift-check against it.

A real example page, written by the export serializer in the test suite, is
[docs/examples/export-page.json](examples/export-page.json) (a Mendelian and a
susceptibility curation, one with clinical diagnostics, one archived row). It validates
against the JSON Schema snapshot [docs/examples/export-page.schema.json](examples/export-page.schema.json);
`backend/tests/api/test_export_example.py` fails when either is stale. Pin both by commit
for importer fixtures.

## Who sees what

The same visibility rule as the Gene Catalogue, enforced again by row-level security:

| Caller | Rows |
| --- | --- |
| Anonymous | Active curations of active public scopes only (no archived or deleted rows) |
| Signed in (JWT or personal access token) | Also active **and archived** curations of scopes where the caller has an accepted membership |

Platform admins get no bypass. `methodology.version` and `version_id` are set for every
caller. Archived rows are history of a scope's work, and curation row-level security (050)
shows non-members active curations only, so there is no public-archive flag: use a personal
access token of a scope member to see archived rows.

`evidence`, `scores` and `summary` are set for scope members. Anyone else, anonymous callers
included, gets them only when the scope is public and a scope admin turned on **Export
evidence publicly** (`export_evidence_public`, off by default; turning it on needs a
signed-in person, not a token or MCP call, as does making a scope with it on public); otherwise
they are `null`.

## Parameters

| Parameter | Meaning |
| --- | --- |
| `scope_name` / `scope_id` | Limit to one visible scope (404 with suggestions when unknown) |
| `updated_since` | ISO 8601; rows whose `updated_at` is at or after it. URL-encode `+` in offsets |
| `cursor` | `next_cursor` of the previous page, passed unchanged (opaque, URL-safe) |
| `limit` | Page size, 1-500, default 100 |

Rows are ordered by `updated_at`, then an internal id. `next_cursor` is `null` on the last
page. Keep the last `updated_at` you processed. `updated_at` is set at transaction start,
so a slow commit can land behind a timestamp you already saw: start each incremental sync a
few minutes before that `updated_at` and de-duplicate by `curation_id` (duplicates are
harmless).

## Row fields

`curation_id`, `entity_key`, `url`, `status` (`active` or `archived`), `scope_name`,
`hgnc_id`, `approved_symbol`, `disease_name`, `mondo_id`, `mode_of_inheritance` (HPO CURIE of the canonical MOI, as entered only when none maps), `mode_of_inheritance_entered`,
`moi_hpo_id` (HPO CURIE of the canonical MOI), `relationship_type`, `risk_allele`,
`computed_verdict`, `final_classification`, `curator_classification_rationale`,
`genetic_score`, `experimental_score`, `association_score`, `total_score`, `methodology {schema_name, version, version_id}`, `pmids`
(every PMID under a `pmid` key in the evidence, deduplicated, numerically sorted),
`curator_name`, `reviewer_name` (who approved), `approved_at`, `activated_at`, `archived_at`,
`archive_reason`, `updated_at`, `evidence`, `scores`, `summary` (see Who sees what), `adoption`, `clingen_reference`,
`synopsis`, `contributions`, `evidence_lines` (see Provenance).

- **Synopsis:** `synopsis` is the entity's synopsis (like SysNDD's clinical synopsis): the
  text of the field the methodology names in `ui_configuration.synopsis_field` (the KGDB and
  ClinGen bundles name `evidence_summary`), trimmed. `null` when the schema names none, the
  field is blank, or `evidence` is hidden from the caller (same rule).

- **Entity:** `entity_key` is `MONDO|MOI`, plus `|SUSCEPTIBILITY` for susceptibility entities
  (then `|ALLELE` when the precuration names a risk allele, exported in its canonical form,
  `rs<digits> <BASE>` for an rsID (e.g. `"rs4664308 A"`; other allele names trimmed, whitespace
  collapsed), in `risk_allele`, null for Mendelian entities), and `''` without a MONDO id. `mondo_id` is exported as `MONDO:nnnnnnn`
  (a typed `MONDO_` is normalised). Treat it as an opaque match key; do not split it on `|`. Use
  `mondo_id`, `moi_hpo_id` and `relationship_type` (`mendelian` or `susceptibility`, default
  `mendelian`) for the parts.
- **Classification:** `computed_verdict` is the class the scoring engine computed.
  `final_classification` is the curator's classification when one was set and approved, else
  `computed_verdict`; publish this one. `curator_classification_rationale` explains a curator
  class that differs from the computed one. There is no separate `curator_classification`
  field: `final_classification` differing from `computed_verdict` marks an override.
- **Class keys:** compare classes by key: trimmed, lowercase, spaces and hyphens as
  underscores (`No Known Disease Relationship` is `no_known`). A schema can declare its own
  classification vocabulary, so expect classes beyond the ClinGen list and do not reject
  unknown ones.
- **Scores:** `genetic_score` and `experimental_score` are the ClinGen
  `genetic_evidence_total` and `experimental_evidence_total`; for custom point models without
  those keys, the model's `genetic_total` and `experimental_total`. `association_score` is a
  susceptibility model's `association_total` (still in `scores` too). `null` when the schema
  has no such section.
- **Evidence:** `evidence` is the curation's evidence as stored, keyed by the field ids of
  the methodology version `methodology.version_id`, non-scoring sections (for example a
  clinical diagnostics section) included. Import it as an editable draft. It includes any
  free text a curator entered in schema fields (rationales, notes); turn on
  `export_evidence_public` only when that is fine to publish. Reviewer comments and LLM
  findings are stored elsewhere and never exported.
- **Score trace:** `scores` is the engine output as stored: the totals above plus, for
  point-model engines, `trace`, whose `sections[].categories[].types[]` give each evidence
  path's item count and summed points; `trace.total` is `total_score`. `trace.rules_applied`
  lists the row rules and step rules that set points, `trace.capped_groups` the capped groups. `scores.warnings`
  holds the scoring warnings.
  `summary` is the engine's verdict summary.
- **Adoption:** `adoption` is `null` unless the curation adopted a ClinGen classification
  (#105). Then it is a GA4GH VA-Spec 1.0 style statement: `id` (the `CGGV:assertion_…`),
  `classification`, `moi`, `mondo`, `reportedIn: [{documentType, title (ClinGen's recommended
  citation), urls: [permalink]}]`, `contributions: [{contributor: {name, agentType, id?},
  activityType: {name, primaryCoding: {system: SEPIO, code}}, date}]` (the ClinGen expert panel
  as organization `interpreter` SEPIO:0000331, the adopting curator as person `curator`
  SEPIO:0000156, the approving reviewer as person `approver` SEPIO:0000155) and `extensions`
  with the record's `retrieved_at` and `record_sha256`. An adoption is not scored here: `computed_verdict`,
  the scores and `scores` are `null` and `final_classification` is ClinGen's class (#613). An
  AI agent that adopted it over MCP appears in the top-level `contributions` as software
  `curator` on behalf of the curator.
- **ClinGen reference:** `clingen_reference` is `null` unless a curation of our own cites
  ClinGen's classification of the same entity. Then it has the shape of `adoption`, but its
  `contributions` hold only the ClinGen expert panel as `interpreter` (with ClinGen's
  classification date): our curator and reviewer are in the top-level `contributions`. A
  `final_classification` other than ClinGen's carries `curator_classification_rationale`.
- **Archive reason:** `archive_reason` is `"Replaced by new active curation"` or
  `"Curation deleted"`; `null` on active rows.

## Provenance (GA4GH VA-Spec 1.0, ClinGen SEPIO roles)

`contributions` (per curation) and `evidence_lines` (per evidence row) use VA-Spec 1.0
field names. `evidence_lines` is `null` where `evidence` is (see Who sees what).

| Gene Curator | Export field | VA-Spec / standard |
| --- | --- | --- |
| Curation author (`curator_name`, created) | `contributions[]` with `activityType.name: curator` | `Contribution`, SEPIO:0000156 |
| Each approving review the caller may see | `contributions[]` with `activityType.name: assessor` | SEPIO:0000154 |
| Approving reviewer (`reviewer_name`, `approved_at`) | `contributions[]` with `activityType.name: approver` | SEPIO:0000155 |
| AI agent of an MCP write (`agent` block) | `contributions[]` with `contributor.agentType: software`, `actedOnBehalfOf` the person | PROV-O `SoftwareAgent`, `actedOnBehalfOf` |
| Model, agent, tools used | `contributor.name`, `contributor.description`, `contributor.extensions[{name: tools_used}]` | `Agent`, `Entity.extensions` |
| Evidence table row | `evidence_lines[]` with `path` (e.g. `genetic.probands[0]`) and `row_id` | `EvidenceLine` |
| Row direction cell `direction` | `directionOfEvidenceProvided` (`supports`, `disputes`, `neutral`) | `EvidenceLine.directionOfEvidenceProvided` |
| Row `source` cells | `evidence_lines[].sources[]`: `documentType` (kind), `id`, `title`, `urls`, `pmid`, `doi`, `citation`, `retrieved_at`, `tool`, `record_sha256` | `Document` (`reportedIn`), plus GeneFoundry provenance |
| Row added / last changed by | `evidence_lines[].contributions[]` (`curator`, date of the write) | `Contribution` |

`activityType` is `{name, primaryCoding: {system: "SEPIO", code}}`: curator SEPIO:0000156,
assessor SEPIO:0000154, approver SEPIO:0000155, interpreter SEPIO:0000331, publisher
SEPIO-CG:97010. `date` is an ISO 8601 date-time in UTC with a `Z` suffix, like the other
export timestamps (a bare source date such as ClinGen's classified date is midnight UTC).
An assessor is listed only for an approving review the caller may see, so adopted
curations and anonymous callers get none. Software contributions are always `curator`, never `approver`: the approver
is the person who approved (4-eyes). They come from the evidence rows' provenance, so callers who
get no `evidence_lines` (non-members while `export_evidence_public` is off) get no software
contributions either. Persons carry no `id`.

The `source` field type (schema-driven, a table cell or a list) checks the identifier per
kind: PMID digits; DOI `10.\d{4,9}/\S+`; ClinVar `(VCV|RCV|SCV)\d{9}(\.\d+)?`; ClinGen allele
`CA\d+`; ClinGen validity `CGGV:assertion_…`; `url` an http(s) URL; `database` any record
name. Gene Curator never fetches the record: store GeneFoundry's `provenance`, `raw_sha256`,
permalink and `recommended_citation` as `retrieved_at`, `record_sha256`, `url` and
`citation`. Row authorship (`added_by`, `added_at`, `changed_by`, `changed_at`; an MCP
agent under `agent`) is computed by the server and kept beside the evidence (the curation's
`row_provenance`), so `evidence` stays exactly what was entered.

## Changes

- **Re-curation:** the new curation appears as a new `active` row; the replaced one gets
  `archived_at` and `status: archived` (members only). Match rows by `entity_key` within a
  scope and gene.
- **Retraction:** retracted curations are hard deletes and never appear. To catch them, and
  archivals an anonymous caller cannot see, run a full sync (no `updated_since`) periodically
  and drop rows that are no longer returned.
- **Deletion:** a deleted curation stays in the feed as `status: archived` with
  `archived_at` set and `archive_reason: "Curation deleted"` (members only); the delete
  counts as a change, so `updated_since` returns it. Retract rows that get `archived_at`.

## Versioning

`export_version` is `"1"`. Fields may be added within v1 (v0.11.0 added `relationship_type`,
`final_classification` and `curator_classification_rationale`; v0.12.0 added `evidence`, `scores`
and `summary`; v0.13.0 added `adoption` (#105), `contributions`, `evidence_lines` and
`synopsis` (#593), `risk_allele` and `association_score` (#614)); consumers must ignore unknown
fields. A generated example page and its JSON Schema are in `docs/examples/`
(`export-page.json`, `export-page.schema.json`). Renaming, removing or changing the meaning of a
field publishes a new version at a new path.
