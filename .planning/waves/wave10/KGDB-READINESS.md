# KGDB readiness: curate kidney genes and build the KGDB schema in Gene Curator

Checked 2026-10-30 against GC `origin/master` 4955a3a3 (Wave 10 #570, #572, #573 merged; #574 open) and
KGDB `main` 55da710. Sources: KGDB [#439](https://github.com/berntpopp/kidney-genetics-db/issues/439)
(spec + 7 comments), [#448](https://github.com/berntpopp/kidney-genetics-db/issues/448),
[#437](https://github.com/berntpopp/kidney-genetics-db/issues/437), the alpha spec folder
[`.planning/specs/2026-10-30-curation-alpha/`](https://github.com/berntpopp/kidney-genetics-db/tree/main/.planning/specs/2026-10-30-curation-alpha)
(`point_model_draft.json`, `BRIEF_CURATOR_DRAFT.md`, `BRIEF_DIAGNOSTICS.md`, `BRIEF_JUDGE.md`).
**KGDB has no full schema file**: only the point model (draft iteration 1) plus prose briefs. No GC file holds one either.

## 1. KGDB methodology (alpha, draft iteration 3; no version numbers)
- **Workflow:** 0 adopt ClinGen where CGGV has curated the entity (reviewer confirms) -> 1 precuration (agent pre-fills
  via GeneFoundry + KGDB, curator decides) -> 2 evidence rows (no PMID = 0 points) -> 3 class from bands, curator
  proposes final class, human reviewer approves. Pipeline: curator agent -> judge agent (row comments, never approves) -> human.
- **Precuration fields:** HGNC gene; MONDO entity; MOI as HPO CURIE; lump/split + rationale + replaced MONDO terms;
  binning (isolated / variable single organ / syndromic); mechanism (LoF/GoF/DN/unknown); kidney relevance,
  `cakut_subtype` (upper/lower); OMIM/Orphanet ids; `relationship_type` mendelian | susceptibility.
- **Evidence (genetic, cap 12):** probands (default 1, cap 10; variant, variant_class lof/missense/..., zygosity,
  phase, de_novo, variant_source, duplicate_of, pmid), segregation (one row, summed LOD 2/3/5 -> 1/2/3, cap 3),
  cohort (2, cap 4). **Experimental (cap 6):** models (2, or 1 for KO-vs-AD-LoF / morpholino; cap 4), functional (1, cap 2).
  Contradictory rows (impact disputed/refuted/minor, source paper/gnomAD/ClinVar); `replicated_over_time`;
  `reported_not_scored`; context only (STRING/GTEx/MGI, never scored). Total cap 18.
- **Row rules:** de novo confirmed 1.5; 0 points for variant_source not_given, compound-het phase unknown,
  AF above max credible (1e-4 AD/XL, 2.5e-3 AR), duplicate rows; at most 2 points per recurrent variant.
- **Bands:** definitive >=12 + replicated; strong >=12; moderate >=7 **and genetic >=4**; limited >0; no_known 0;
  overrides contradictory disputed/refuted. Reviewer flags: band edge +-2, hotspot (>=50% proband points from <=2
  variants), experimental > genetic, susceptibility. Susceptibility: own vocabulary established/likely/uncertain, off the Mendelian bands.
- **Diagnostics section (non-scoring):** `recommended_transcript` {refseq, ensembl, mane_status, legacy_transcript,
  numbering_conversion}; `detectability[]` {challenge, share_of_variants, methods, tools[{name,url,pmid}], negative_report_does_not_exclude};
  `resources[]` {type, name, url, language, audiences[], maintainer, conflict_of_interest, verified{method,date}}.
- Calibration (27 ClinGen genes): 67% exact, 81% within one class, so it is an agent proposal with mandatory human review.

## 2. KGDB requirement -> GC support today
| Requirement | GC | Where |
|---|---|---|
| Sections/categories/types, caps, total cap, bands first-match, `requires` | yes | `backend/app/scoring/point_model.py`, `core/schema_rules.py:_check_point_model` |
| Genetic >=4 for Moderate+ | yes (JSON-only) | band `section_min` (#556), `schema_rules.py:BAND_KEYS` |
| Max 2 points per recurrent variant | yes (JSON-only) | type `group_by` + `group_cap` (#557) |
| Reviewer flags band edge / hotspot / exp > gen | yes (JSON-only) | `point_model.review_flags` (#559, PR #572) |
| No PMID / no real variant scores 0 | yes | `evidence_items.uncited`, `require_variant` (#535) |
| Contradictory override by impact | yes | `overrides[{when, field, in, class}]` |
| Schema vocabulary incl. susceptibility classes | yes (JSON-only) | `scoring_configuration.classifications` (`scoring/classifications.py`) |
| relationship_type, entity key HGNC+MONDO+MOI(+SUSCEPTIBILITY) | yes | precuration fields `mondo_id`, `mode_of_inheritance`, `relationship_type` (flat or under `entity_definition`): `models/curation.py:ENTITY_KEY_SQL` |
| Susceptibility scored on its own tiers | partial | second curation schema; UI picks it by hand (`CurationFormView.vue` schema priority 2); no routing by relationship_type |
| Curator final class + reviewer approval, human-only approvals | yes | #533, #560 (scope `approvals_require_session`) |
| De novo 1.5; zero for not_given / phase unknown / AF cap / duplicate | workaround | `range` + curator-entered points; fields do not drive points |
| Segregation summed LOD 2/3/5 -> 1/2/3 | workaround | `rule: explicit_points`; built-in LOD rule is SOP v11 (#447) |
| url fields, MONDO/OMIM checks, show_when, llm_share | yes (JSON-only) | `VALID_FIELD_TYPES`, `llm/sharing.py` |
| Diagnostics nested lists (`tools[]`, `audiences[]` inside a row) | missing | table cells fall back to text: `components/dynamic/componentRegistry.ts:cellFor` |
| Publish-time scoring tests | yes (JSON-only) | `scoring_configuration.tests` (`crud/schema_repository.py:_test_failures`) |
| Build fields/sections/ui_configuration in UI | missing | `views/SchemaEditor.vue` has 2 raw JSON textareas (field_definitions, scoring) only |
| Publish a methodology version from UI | **missing** | no client call for `POST /curation-schemas/{id}/versions` (`api/schemas.ts`); curations pin the latest *published* version (042), so UI edits never reach curators |
| Import a schema file | JSON-only | `POST /schemas/curation-schemas` (400 on existing name+version), then publish, then `POST /workflow-pairs`, then `update_scope`; not idempotent; same tools on `/mcp/full` (admin) |
| Scope default workflow pair | yes | `components/scope/ScopeSettings.vue`, `create_scope/update_scope` MCP |
| Export evidence/scores/summary/diagnostics | yes | `docs/EXPORT.md`, #558 (members, or `export_evidence_public`) |
| Step 0 adopt ClinGen | workaround | url + select + curator class; native take-over is #105 (open) |
| KGDB import adapter, contract pin, uniqueness incl. relationship_type | missing (KGDB) | KGDB #448 open; `uq_gda_gene_disease_moi` is still (gene, disease, moi) |

## 3. Gaps
**Schema expressiveness (backend)**
- Row point rules driven by field values (`points_when: [{field, in, points}]`): de novo 1.5, not_given/phase unknown/duplicate 0,
  numeric AF above cap 0. This removes 5 hand-entered workarounds.
- Step rule on a numeric field (`rule: step`, `field: summed_lod`, steps 2/3/5 -> 1/2/3). Related to #447; does not close it.
- Static cross-checks the validator lacks: point-model `types[].path` must name an existing evidence table, `show_when`
  targets and override `field` must exist, select defaults must be in options. Today a typo scores 0 silently.
- Engine name: a non-ClinGen point model must declare `engine: clingen_sop_v11` (`scoring/registry.py`). A neutral `point_model` alias would remove the misleading label.
- Array/multiselect columns inside evidence tables (frontend cell + backend validation), or flatten diagnostics to one row per tool/audience.

**Schema builder UI** (#219 and #282, neither started)
- Field/section list editor (type, required, options, show_when, help, llm_share, evidence-table columns), live preview with
  `DynamicForm`, Advanced JSON tab for all 5 blocks (`ui_configuration`, `validation_rules`, `workflow_states` are not editable today).
- Point-model builder: tables for sections/categories/types (default, range, cap, group cap, require_variant), bands
  (min, requires, section_min), overrides, review_flags, classifications; inline diagnostics; run `tests`.
- **Publish version** button with diagnostics and `/versions/{id}/impact` preview (blocker: without it a UI-built schema stays at its stub v1).

**API/MCP import path**
- One idempotent admin endpoint `POST /schemas/methodologies/import` taking a bundle {precuration schema, curation schema(s),
  workflow pair, optional `scope_name` + `set_default`} with `dry_run`. Match by name; create, or update and publish a new
  version only when the snapshot changed; upsert the pair; set the scope default. Returns ids, versions and diagnostics.
  It appears on `/mcp/full` automatically; add it to the core `/mcp` list only if agents should import (owner question 4).
- UI: "Import methodology file" on `SchemaManagement.vue` plus the existing JSON download in `SchemaEditor.vue` = round trip.

**KGDB methodology artifact** (none exists in either repo)
- `docs/schemas/kidney-genetics/` bundle: precuration (KGDB precuration columns, entity field names as above), Mendelian curation
  (point model + section_min + group cap + review_flags + diagnostics section), susceptibility curation (vocabulary
  established/likely/uncertain), workflow pair(s). Embed `tests` from the pilot (CLDN16 definitive, NEK8 strong, SIX5
  disputed, DNAJB11-like moderate -> limited by section_min, hotspot capped). A pytest runs `publish_errors` on every file.
- Field ids are the KGDB import contract (KGDB maps `evidence.diagnostics.*`), so freeze them in the README of the bundle.

**KGDB sync side (#437/#448, KGDB repo)**
- Pin `CurationExportPage` with a drift check; import drafts by `(scope_name, hgnc_id, entity_key)`; full-sync retraction
  (deletions never appear in the feed); add `relationship_type` to `uq_gda_gene_disease_moi`; map schema class keys and
  the artifact's diagnostics field ids; use a member PAT (otherwise evidence and `methodology.version` are hidden).

## 4. Wave 11 workstreams (disjoint file ownership)
| WS | Size | Owns | Delivers | Closes |
|---|---|---|---|---|
| A import | M | new `api/v1/endpoints/methodology_import.py`, new `crud/methodology_import.py`, register in `api/v1/api.py`, `mcp/server.py` list, tests | idempotent bundle import + dry run + scope default | part of #282 (code path) |
| B rules | M | `scoring/point_model.py`, `core/schema_rules.py`, `scoring/registry.py`, tests | `points_when`, `rule: step`, path/show_when cross-checks, `point_model` engine alias | refs #447 |
| C field editor | L | `views/SchemaEditor.vue` (split into new `components/schema-editor/*` except `scoring/`), `stores/schemas.ts`, `api/schemas.ts` | field/section editor, preview, Advanced JSON (5 blocks), Publish version + impact | #219 |
| D point-model builder + import UI | M | new `components/schema-editor/scoring/*`, `views/SchemaManagement.vue` | table builder with diagnostics + tests run; Import file button (calls A) | rest of #282 (table views; canvas stays out) |
| E KGDB artifact | S | new `docs/schemas/kidney-genetics/*`, new `backend/tests/unit/test_kgdb_methodology.py` | ready-to-import bundle with tests, README of field ids | KGDB #439 "methodology created in GC" |
| F cells | S | `components/dynamic/componentRegistry.ts`, `EvidenceTableField.vue` | multiselect/array cells in tables | none (new issue) |

Order: B and F before E's final JSON (E can ship first with `explicit_points` workarounds); D lands before C mounts
`components/schema-editor/scoring/PointModelBuilder.vue`; A before D's import button (`make api-types`). KGDB #448 runs in
parallel in the KGDB repo against E's field ids. #105 (native ClinGen take-over) and #216 remainder stay open.

## 5. Owner questions
1. Susceptibility: a second curation schema the curator picks by hand, or route by `relationship_type` automatically (needs code)?
2. Artifact: import via API only, or also seed it on fresh databases with a numbered SQL migration (and in production)?
3. Draft-4 row rules: make de novo / zero-when / LOD steps native (WS B), or keep curator-entered points under `explicit_points`?
4. Who may import: platform admin on `/mcp/full` only, or also agents on core `/mcp` and scope admins for their own scope (#284)?
