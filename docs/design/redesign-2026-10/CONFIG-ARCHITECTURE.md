# Config-driven methodologies: language, versions, provenance, migration

Status: proposal, 2026-10-21. Builds on the code reviews in [`research/backend-config-review.md`](research/backend-config-review.md)
and [`research/frontend-config-review.md`](research/frontend-config-review.md). Screens:
[Methodologies](renders/Methodologies.png), [Derive](renders/ModalDerive.png), [Workflow builder](renders/Workflows.png)
([table](renders/Workflows-table.png), [code](renders/Workflows-code.png)), [Form builder](renders/FormBuilder.png),
[Point system](renders/Scoring.png), [Studio](renders/Studio.png).

## 1. Goal

Everything a curation team can disagree about is configuration, not code:

- which **stages** a gene goes through, who acts, what moves it on or back (workflow);
- what each stage **asks** (steps, fields, conditions, help) and how the page looks (forms);
- how evidence turns into **points** and a **classification** (point model, including categories a team invents);
- the **examples** that must keep their result (tests).

One versioned **methodology** holds all four. Curators always see pages generated from it. ClinGen SOP v11 is a
shipped template, not a special case in code.

## 2. Where we are (summary of the reviews)

| Concept | Today | Evidence |
| --- | --- | --- |
| Storage | 5 JSON columns on `curation_schemas`, edited in place by `PUT`; no version pinning on curations | backend review §1, §7 |
| Scoring config | Only `scoring_configuration.engine` is read. Caps and bands are hard-coded in `scoring/clingen.py:38-68`. 9 calculators (5 FE, 4 BE), 3 band sets, none SOP-correct | #157, backend §2 |
| Stored score | Trigger `calculate_schema_scores` nulls `computed_verdict` on every non-draft write | #234 |
| Engine lookup | Validator scores only for engine `"clingen"`; seed says `"clingen_sop_v11"`, so validation never scores | `schema_validator.py:798`, `020_complete_sop11_schema.sql:785` |
| Workflow | Hard-coded transition table `workflow_engine.py:39-60` plus a competing DB trigger; no precuration→review edge | #229, #237 |
| Forms | Generic `DynamicForm` renders nothing (#227) and the JSON-schema endpoint strips labels, widgets, layout. ClinGen form is ~3,100 hand-written lines duplicating the seed's `EvidenceTable` config | frontend review §1–2 |
| Validators | 3 validators, 3 type vocabularies; seeds pass none of them | #207 |
| Editors | Raw JSON textareas; save and validate errors only logged | #208, #219 |
| Data | `evidence_data` exists in 4 shapes (dev DB) | backend §8 |

The good news: the seed `020_complete_sop11_schema.sql` already describes most of the ClinGen form and point model as data.
The work is making code **read** it, then giving it a proper home, a language and editors.

## 3. Object model

Every object has a stable **key** and a **path** (`scoring.genetic.proband.null`, `form.precuration.moi`). Keys never
change silently: a rename is written `renamed from old_key` and produces a data migration.

```
Methodology            name, owner scope, visibility
└─ Version             semver, status draft|published|retired, source text, compiled JSON, sha256,
                       derived_from (version + sha), tracks_upstream, author, reason, created_at, diff summary
   ├─ forms            one per stage kind that collects data
   │  └─ step          ordered
   │     └─ field      key, type, label, help, required [when expr], visible when expr, validation,
   │                   options, ontology root, default, computed = expr
   ├─ scoring          mode points | qualitative
   │  ├─ section       key, label, cap                       (genetic, experimental, … user-defined)
   │  │  └─ category   key, label, cap, combine sum|max, fed by form table or row type
   │  │     └─ type    key, label, default, range, step, explain_above_default
   │  ├─ shared cap    [paths] ≤ n                           (models + rescue.* ≤ 4)
   │  ├─ counts when   expr over an item                     (status = score and has pmid)
   │  └─ classify      ordered bands (name, from, to, extra condition) + curator-asserted classes
   ├─ workflow         stages (kind, name, form ref, actors), transitions (to, when expr, back), effects
   └─ tests            given items → expect total, section values, class
```

Field types (registry, one entry per type: editor component, compact table-cell component, empty value, validator):
`gene` (HGNC), `disease` (MONDO), `phenotypes` (HPO, optional root), `publication` (PMID with citation lookup),
`variant` (HGVS), `choice`, `multi_choice`, `text`, `markdown`, `bool`, `number`, `date`, `computed`,
`evidence_table` (columns are fields; rows carry `status` and points; feeds a scoring category).

## 4. The language

A small, line-oriented, indentation-scoped language. Goals: readable by curators, diffable in review, round-trips
exactly with the visual editors, no general-purpose computation.

```
methodology "Kidney GDV" version 1.1.0
  derived from "ClinGen GDV" 1.0.0 track upstream
  reason "Add patient registry evidence; no rescue in human"

form precuration
  step "Gene and disease"
    field gene    : gene required
    field disease : disease required
  step "Inheritance"
    field moi      : choice(AD, AR, XLD, XLR, MT, other) required
      help "Use the MOI reported for the disease entity"
    field moi_text : text required when moi = other
  step "Lumping and splitting"
    field assertions : list of disease min 1
    field rationale  : markdown required when count(assertions) > 1

form curation
  step "Genetic"
    field proband : evidence_table
      column id      : text required
      column variant : variant required
      column pmid    : publication required
      column kind    : choice(null, other) required      # picks the evidence type
    field registry : evidence_table
      column cohort  : text required
      column size    : number min 1
      column pmid    : publication required

scoring points
  counts when status = score and has pmid and within range
  explain when points > default
  section genetic cap 12
    category proband cap 12 from curation.proband by kind
      type null  default 1.5 range 0..3   step 0.1
      type other default 0.1 range 0..1.5 step 0.1
    category segregation cap 3 lookup lod_table(summed_lod, method)
    category registry cap 2 from curation.registry
      type cohort default 1 range 0..2
  section experimental cap 6
    category function cap 2 …
    category models  …
  shared cap 4 : models + rescue.*
  classify
    limited   1  .. <7
    moderate  7  .. <12
    strong    12 .. 18
    definitive 12 .. 18 when replicated_over_time
    no_known  when total = 0
    asserted disputed, refuted reason required

workflow "Kidney standard"
  stage entry by scope_admin then precuration
  stage precuration form precuration by curator
    then curation when approved_by reviewer
  stage curation form curation by curator
    then review when valid and every scored_item has pmid
  stage review reviewers 1 not author
    then expert_panel when class = disputed
    then active when approved
    back curation when changes_requested
  stage expert_panel quorum 2 of panel then active when approved
  stage active unique (gene, disease, scope) recurate after 3y

test "two null probands"
  given proband [null 1.5, null 2.0] function [0.5]
  expect total 4.0 class limited
```

Expressions are a closed set: comparisons, `and/or/not`, `in`, `count/sum/min/max`, `every/any … has …`, field
references, literals. No loops, no user functions, no I/O. One evaluator in Python is the source of truth; a TypeScript
port is added only if live scoring latency proves it necessary (frontend review §5).

**Static checks on compile** (shown as line:col diagnostics in the code view and as badges in the visual editors):
unknown references; duplicate keys; every stage reachable and with an exit; exactly one end state; author never reviews
when four-eyes is required; caps ≥ 0 and section caps ≥ largest category cap; default inside range; bands ordered,
non-overlapping, covering the score range; every scored category fed by exactly one form table; roles exist in the
target scopes (warning); key renames have a migration; all tests pass.

## 5. Text, compiled form and editors

- **Backend owns the language.** One Python package: `parse → AST → check → compile → IR (JSON)` and
  `format(IR) → canonical text`. Endpoints: `POST /methodology/compile` (diagnostics), `POST /format`, `POST /test`,
  `POST /explain` (score trace for one curation), `GET /methodologies/{id}/versions/{v}/compiled` (immutable, cached by sha).
- **Visual editors edit the IR**, then call `/format` to refresh the code tab. Text is never parsed in the browser, so
  there is exactly one parser. The code tab uses CodeMirror 6 with diagnostics from `/compile`.
- **Workflow builder:** canvas, table and code are three views of one IR; clicking a stage opens its form builder
  (precuration, curation) or scoring editor.
- Generated TS types for the IR come from OpenAPI (`make api-types`), like the rest of the API.

## 6. Versions and provenance

- **Immutable once published.** Editing a published version creates a draft `x.y+1.0`; publish runs checks and tests.
- **Pinning.** Every precuration and curation stores `methodology_version_id` and the sha. It is rendered, validated and
  scored with that version forever, unless explicitly upgraded.
- **Derive.** "Derive from…" copies a version into a new methodology with `derived_from = (version, sha)`, author, reason.
  `track upstream` keeps a link: when the parent publishes, the child sees a three-way diff (base = parent version it
  derived from, ours = child, theirs = new parent) and pulls changes item by item. Independent copies keep provenance
  but get no offers.
- **Diff on publish.** Stored per version: added, removed, changed objects by path, plus the test results.
- **Upgrade curations.** An audited job re-scores selected curations with the new version, shows the impact
  ("scores change for 4, classification for 1") and requires confirmation. Old results stay in history.
- **Score provenance.** Each saved score stores the version sha and the trace, so "why is this Strong" is answerable later.

## 7. Migration (smallest steps, each shippable)

| Step | What | Removes | Issues |
| --- | --- | --- | --- |
| 0 | Fix what blocks curators today: drop the scoring trigger and store engine results on save; render `DynamicForm` from the raw schema through a normaliser; engine-name lookup; precuration transitions | trigger in `002_schema_triggers.sql`, JSON-schema stripping | #234, #227, #229, #262, #263 |
| 1 | `methodologies` + `methodology_versions` tables (source, compiled, sha, derived_from, author, reason, status); pin curations; import **v0** from today's seeds reproducing current behaviour so no verdict changes silently | in-place `PUT` edits | #265, #284 |
| 2 | Scoring interpreter over the IR point model (user-defined sections, categories, types, shared caps, bands, qualitative mode); publish **ClinGen GDV 1.0.0** (SOP-correct) as an audited upgrade | `scoring/clingen.py` constants, 8 duplicate calculators | #157, #266 |
| 3 | Form interpreter: field-type registry, steps, conditions, `evidence_table`; render ClinGen from config | `components/clingen/**` (~3,100 lines), `use_dynamic_form` switch, 17 column arrays | #232, #239–#241, #245, #267 |
| 4 | Workflow interpreter: stages, transitions, gates, effects from IR; one transaction per transition | hard-coded transition and role tables, `manage_workflow_transitions` trigger | #229, #237, #116, #268 |
| 5 | Language: compiler, formatter, checks, tests, explain; CodeMirror code views | 3 validators | #207, #208, #269, #270 |
| 6 | Visual builders: methodologies and lineage, form builder, point model, workflow canvas and table; derive and upstream merge; curation upgrade jobs | raw JSON editors | #219, #120, #118, #216, #271 |

Keep today's `evidence_data` paths as field keys in v0, so step 1 needs no data migration. Normalising the four
`evidence_data` shapes happens once, inside the step-2 upgrade job, after a read-only census on production.

## 8. Risks

- Classifications of active curations change under SOP-correct bands; handled by v0 pinning and an audited upgrade.
- RLS on the new tables cannot be tested while the dev role is a superuser (#156); use `make test-postgres`.
- Applied migrations are not tracked yet (#158); land that first or alongside step 1.
- The language must stay small. Anything that needs real code becomes a new field type or a new effect in the
  registry, reviewed like any other code.

## 9. Permissions (decided 2026-10-21, #284)

Rights are granular and scope-aware. Code checks **capabilities**, never role names: one dependency
`require(capability, scope_id | resource)` replaces the scattered admin and scope-role checks. A role → capability
matrix is data (seeded default, later editable by platform admins).

- **Ownership:** methodologies, versions and workflows carry `owner_scope_id`; `null` means a global template.
- **Platform admins** create and publish global templates and manage everything.
- **Scope admins** derive methodologies, create workflows, publish versions and assign them, for scopes they
  administer only (interim rule for workflow pairs in #212).
- **Curators, reviewers, viewers** use configuration but never change it; reviewers never review their own work.
- The same matrix drives API checks, RLS policies and what the Setup area shows; permission-relevant actions are
  audited with actor, capability and scope.
