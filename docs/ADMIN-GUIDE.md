# Admin guide

One page for platform admins and scope admins. Installation, upgrades and backups are in the
[README](../README.md); per-version upgrade steps in [docs/releases/](releases/).

## Two kinds of admin

- **Platform admin** (`application_role = admin`): users, global templates and workflows,
  methodology import, *Move to version*, LLM configuration. No bypass of the 4-eyes rule or of
  row-level security: a platform admin reviews only as a scope reviewer, and never their own work.
- **Scope admin** (scope role `admin`): members and invitations, gene assignments, scope
  settings, and the scope's own methodologies and workflows.

## Who may do what

Scope roles map to capabilities stored in the `role_capabilities` table (migration 082); the
API and the RLS policies read the same rows.

| Scope role | Capabilities |
| --- | --- |
| viewer | `scope.view` |
| reviewer | viewer + `curation.review` |
| curator | viewer + `curation.edit`, `gene.create` |
| admin | viewer + review, edit, `gene.assign`, `gene.create`, `scope.members.manage`, `scope.manage`, `methodology.derive`/`edit`/`publish`, `workflow.create`, `workflow.assign_to_scope` |

Anything without a scope (global templates, shared data) needs a platform admin.
Configuration changes are written to the audit log with actor, capability and scope.

## Set up a scope

1. Create the scope under **Scopes** and invite members with their scope role (also from
   **User Management**).
2. **Methodology.** Import a bundle as a platform admin (**Templates**, *Import methodology*,
   dry run first; format in [METHODOLOGY-IMPORT.md](METHODOLOGY-IMPORT.md)): the ClinGen SOP v11
   and KGDB bundles are in [docs/schemas/](schemas/). Or, as a scope admin, derive a global
   template into your scope and edit it in the schema editor (Fields, Workflow and Scoring tabs;
   problems in the unsaved draft show inline). **Publish version** is blocked on errors.
3. **Workflows.** In scope settings, set the *Workflow pair* (the default) and *Other
   allowed workflows*. Curators can only start work in these pairs.
4. **Genes.** Assign genes to curators with due dates (paste a list, or bulk-assign).
5. **Export.** Members' tokens export evidence; turn on *Export evidence publicly* only for a
   public scope that should share it ([EXPORT.md](EXPORT.md)).

## Change a methodology

Edits publish a new methodology version; existing curations keep the version they started
on. To move them, use *Move curations to the latest version* on the schema row: the dry run
lists, per curation, fields kept and dropped, newly empty required fields and the old and new
score and class. Applying it rescores in one audited transaction; an active curation whose class
changes reopens in review, and you cannot review a curation you moved. Two admins editing one
schema: the later stale save is refused (409) and the editor keeps your draft.

## Point models

Scoring rules (caps, bands, row rules, step and SOP v11 segregation rules, reviewer flags,
embedded tests) are described in [POINT-MODEL.md](POINT-MODEL.md). Run the embedded tests from
the Scoring tab before publishing.
