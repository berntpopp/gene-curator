# Curation export v1

A read-only feed of reviewed curations for downstream publishers (for example
kidney-genetics-db). Gene Curator stays the source of record; consumers sync from this feed.

```
GET /api/v1/export/curations?scope_name=kidney-genetics&updated_since=2026-01-01T00:00:00Z
```

The response schema is `CurationExportPage` in the OpenAPI document (`/openapi.json`); pin it
and drift-check against it.

## Who sees what

The same visibility rule as the Gene Catalogue, enforced again by row-level security:

| Caller | Rows |
| --- | --- |
| Anonymous | Active curations of active public scopes only (no archived or deleted rows) |
| Signed in (JWT or personal access token) | Also active **and archived** curations of scopes where the caller has an accepted membership |

Platform admins get no bypass. Anonymous callers get `methodology.version = null`
(methodology versions are readable by signed-in users only); `methodology.version_id` is
always set. Use a personal access token of a scope member to see archived rows and versions.

`evidence`, `scores` and `summary` are set for scope members. Anyone else, anonymous callers
included, gets them only when the scope is public and a scope admin turned on **Export
evidence publicly** (`export_evidence_public`, off by default; turning it on needs a
signed-in person, not a token or MCP call); otherwise they are `null`.

## Parameters

| Parameter | Meaning |
| --- | --- |
| `scope_name` / `scope_id` | Limit to one visible scope (404 with suggestions when unknown) |
| `updated_since` | ISO 8601; rows whose `updated_at` is at or after it. URL-encode `+` in offsets |
| `cursor` | `next_cursor` of the previous page, passed unchanged (opaque) |
| `limit` | Page size, 1-500, default 100 |

Rows are ordered by `updated_at`, then an internal id. `next_cursor` is `null` on the last
page. Keep the last `updated_at` you processed. `updated_at` is set at transaction start,
so a slow commit can land behind a timestamp you already saw: start each incremental sync a
few minutes before that `updated_at` and de-duplicate by `curation_id` (duplicates are
harmless).

## Row fields

`curation_id`, `entity_key`, `url`, `status` (`active` or `archived`), `scope_name`,
`hgnc_id`, `approved_symbol`, `disease_name`, `mondo_id`, `mode_of_inheritance` (as entered),
`moi_hpo_id` (HPO CURIE of the canonical MOI), `relationship_type`, `computed_verdict`,
`final_classification`, `curator_classification_rationale`, `genetic_score`,
`experimental_score`, `total_score`, `methodology {schema_name, version, version_id}`, `pmids`
(every PMID under a `pmid` key in the evidence, deduplicated, numerically sorted),
`curator_name`, `reviewer_name` (who approved), `approved_at`, `activated_at`, `archived_at`,
`archive_reason`, `updated_at`, `evidence`, `scores`, `summary` (see Who sees what).

- **Entity:** `entity_key` is `MONDO|MOI`, plus `|SUSCEPTIBILITY` for susceptibility entities,
  and `''` without a MONDO id. Treat it as an opaque match key; do not split it on `|`. Use
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
  those keys, the model's `genetic_total` and `experimental_total`. `null` when the schema
  has no such section.
- **Evidence:** `evidence` is the curation's evidence as stored, keyed by the field ids of
  the methodology version `methodology.version_id`, non-scoring sections (for example a
  clinical diagnostics section) included. Import it as an editable draft. It includes any
  free text a curator entered in schema fields (rationales, notes); turn on
  `export_evidence_public` only when that is fine to publish. Reviewer comments and LLM
  findings are stored elsewhere and never exported.
- **Score trace:** `scores` is the engine output as stored: the totals above plus, for
  point-model engines, `trace`, whose `sections[].categories[].types[]` give each evidence
  path's item count and summed points; `trace.total` is `total_score`. `scores.warnings`
  holds the scoring warnings.
  `summary` is the engine's verdict summary.
- **Archive reason:** `archive_reason` is `"Replaced by new active curation"` or
  `"Curation deleted"`; `null` on active rows.

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
`final_classification` and `curator_classification_rationale`; #558 added `evidence`, `scores`
and `summary`); consumers must ignore unknown
fields. Renaming, removing or changing the meaning of a
field publishes a new version at a new path.
