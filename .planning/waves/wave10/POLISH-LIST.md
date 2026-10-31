# Wave 10 polish list (impeccable PR input)

Primary: the UX section of .planning/waves/wave10/MONKEY-UI-R1.md (per-flow scores and ranked fixes). Lowest first:
KGDB curation 3/10, schema builder 4/10, User Management 6/10, then the rest.

Review nits collected during Wave 10:
- PointModelRowRules: a present:false rule displays as "is one of"; clearing a bound's value writes 0 instead of removing the bound.
- PointModelBuilder Code view: invalid JSON text never reaches the editor's jsonErrors, so Save stores the last valid config without warning.
- SchemaEditor: clicking Edit before the versions request returns can miss the "already published" rename warning (~456).
- evidence_lint hotspot message "from 1 variants" (grammar).
- CurationDetailView warnings list uses :key="w" (duplicate warnings warn); use index.
- Methodology import dry run labels a refused schema "create": add "refused" to IMPORT_ACTIONS in SchemaManagement.vue and the backend label (crud/methodology_import.py), update docs/METHODOLOGY-IMPORT.md.
- WorkflowManagement: version field accepts "v1" (add semver rule if backend expects semver); inactive schema shows raw id.
- stores/workflow.ts WORKFLOW_STAGES: remove unused required_roles and scope_admin (closes #216 with the rest done in #571).
- FAQ.vue bulk-add-genes entry still describes the old Add Genes tab; intake dialog has no due-date field at paste time (add it if small, the API accepts due_date now).
- frontend/src/composables/useHgncSearch.ts and its spec are unused: delete.
- README ~305 points to backend/docs/ which does not exist.
- UI sends a follow-up PUT after creating an assignment; the API accepts due_date on create now: drop the PUT.
- B17 Last Modified shows a dash after save (schema update response needs a fresh updated_at); B19 /users stable sort order.
