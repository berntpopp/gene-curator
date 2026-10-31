# Methodology import

One JSON file holds a methodology: its schemas, the workflow pairs linking them and an
optional scope default. A platform admin imports it with one call:

```
POST /api/v1/schemas/methodologies/import[?dry_run=true]
```

MCP: the `import_methodology` tool on `/mcp/full` (platform admins only; not on core `/mcp`).

## Bundle format

```json
{
  "schemas": [
    {
      "name": "Kidney Precuration",
      "version": "1",
      "schema_type": "precuration",
      "field_definitions": {},
      "validation_rules": {},
      "workflow_states": {},
      "ui_configuration": {},
      "scoring_configuration": null
    },
    { "name": "Kidney Curation", "version": "1", "schema_type": "curation", "...": "..." }
  ],
  "workflow_pairs": [
    {
      "name": "Kidney Workflow",
      "version": "1",
      "description": "optional",
      "precuration_schema": "Kidney Precuration",
      "curation_schema": "Kidney Curation"
    }
  ],
  "scope_default": { "scope_name": "kidney-genetics", "workflow_pair": "Kidney Workflow" }
}
```

- `schemas[]`: the body of `POST /schemas/curation-schemas` (same fields and defaults).
  Names are unique within the bundle.
- `workflow_pairs[]`: schemas are named, not referenced by id, and must be in the bundle.
  The precuration schema is of type `precuration` or `combined`, the curation schema
  `curation` or `combined`.
- `scope_default` (optional): sets that scope's `default_workflow_pair_id`.

The JSON download of a schema in the schema editor is the body of one `schemas[]` entry.

## Behaviour

- Schemas and pairs are matched by `name` + `version`.
- New schema: created and published as methodology version 1.
- Existing schema whose content (`field_definitions`, `validation_rules`,
  `scoring_configuration`, `workflow_states`, `ui_configuration`) equals both its latest
  published version and the bundle: `unchanged`, nothing is written. Changed content
  overwrites the schema and publishes the next version; published versions never change
  and existing curations keep theirs.
- A schema with unpublished edits (differs from its latest version and from the bundle)
  is refused: publish or discard the edits first. Unpublished edits equal to the bundle
  are published as the next version.
- A workflow pair needs active schemas: an inactive bundle schema (`is_active: false`)
  or an inactive existing schema in a pair is refused.
- At most 50 schemas and 50 workflow pairs; pair names are unique within the bundle.
- Pairs pointing at other schemas, or with another description, are updated in place.
- Every schema runs the publish gate (static checks and `scoring_configuration.tests`).
  Any error refuses the whole import: 422 with the report in `detail`, nothing written.
- `dry_run=true` returns the same report and plan (`create`, `unchanged`,
  `new_version`, `update`, with the version each schema would have) and writes nothing.
  An existing schema the import refuses (another schema type, unpublished edits) is
  planned as `refused`; its reason is in `errors`.
- The import is one transaction: all of it or nothing. Each import (not a dry run)
  writes one `audit_log` row (`change_type` `methodology_import`) with the plan.

## Response

```json
{
  "dry_run": false,
  "errors": [],
  "items": [
    { "kind": "schema", "name": "Kidney Curation", "version": "1",
      "action": "new_version", "id": "…", "methodology_version": 2 },
    { "kind": "workflow_pair", "name": "Kidney Workflow", "version": "1",
      "action": "unchanged", "id": "…", "methodology_version": null },
    { "kind": "scope_default", "name": "kidney-genetics", "version": null,
      "action": "update", "id": "…", "methodology_version": null }
  ]
}
```
