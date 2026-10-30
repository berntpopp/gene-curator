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
| Anonymous | Active curations of active public scopes |
| Signed in (JWT or personal access token) | Also active **and archived** curations of scopes where the caller has an accepted membership |

Platform admins get no bypass. Anonymous callers get `methodology.version = null`
(methodology versions are readable by signed-in users only); `methodology.version_id` is
always set. Use a personal access token of a scope member to see archived rows and versions.

## Parameters

| Parameter | Meaning |
| --- | --- |
| `scope_name` / `scope_id` | Limit to one visible scope (404 with suggestions when unknown) |
| `updated_since` | ISO 8601; rows whose `updated_at` is at or after it. URL-encode `+` in offsets |
| `cursor` | `next_cursor` of the previous page, passed unchanged (opaque) |
| `limit` | Page size, 1-500, default 100 |

Rows are ordered by `updated_at`, then an internal id. `next_cursor` is `null` on the last
page. Keep the last `updated_at` you processed and pass it as `updated_since` next time.

## Row fields

`curation_id`, `entity_key` (`MONDO|MOI`, `''` without a MONDO id), `url`, `status`
(`active` or `archived`), `scope_name`, `hgnc_id`, `approved_symbol`, `disease_name`,
`mondo_id`, `mode_of_inheritance` (as entered), `moi_hpo_id` (HPO CURIE of the canonical
MOI), `computed_verdict`, `genetic_score`, `experimental_score`, `total_score`,
`methodology {schema_name, version, version_id}`, `pmids` (every PMID under a `pmid` key
in the evidence, deduplicated, numerically sorted), `curator_name`, `reviewer_name` (who
approved), `approved_at`, `activated_at`, `archived_at`, `updated_at`.

## Changes

- **Re-curation:** the new curation appears as a new `active` row; the replaced one gets
  `archived_at` and `status: archived` (members only). Match rows by `entity_key` within a
  scope and gene.
- **Retraction:** retracted curations are hard deletes and never appear. To catch them, and
  archivals an anonymous caller cannot see, run a full sync (no `updated_since`) periodically
  and drop rows that are no longer returned.

## Versioning

`export_version` is `"1"`. Fields may be added within v1 (a final classification is planned,
#533); consumers must ignore unknown fields. Renaming, removing or changing the meaning of a
field publishes a new version at a new path.
