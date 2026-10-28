# Wave 7 lean audit (MCP core, publications, ontology)

Date 2026-10-28. Base: origin/master 1d2e364d (#517), plus open PR #518. No code changed.
Scope rule: Gene Curator curates and validates; research (papers, abstracts, genotypes,
variants, disease/phenotype lookup) goes through GeneFoundry. Owner-approved and out of
scope: PATs (#462), LLM console and worker (#489), cited-evidence scoring, save/submit validation.

What it does: scope-based gene-disease curation with a 4-eyes review; Wave 7 added an MCP
server that turns REST routes into tools (/mcp core set, /mcp/full everything).
Assumed load: a few curators and agents per scope; the cost here is tokens per agent
session, not server load.

## Measured
- /mcp core: 78 tools, tools/list about 56.6k chars (~15-19k tokens) on every session,
  plus 3.8k chars of instructions (the test cap is 4096).
- Study tool calls (rounds 0-5, 24 Claude runs per round): get_publication 111,
  search_pubmed 41, validate_pmids 52. That is the research work the scope rule moves to
  GeneFoundry, and none of the runs called GeneFoundry.
- 0 calls in all rounds: list_notifications, mark_notification_read,
  get_my_pending_invitations, accept_invitation, get_scope_details, update_scope,
  update_member_role, get_genes_by_symbol, search_genes, get_gene, search_hgnc_genes,
  fetch_hgnc_gene, get_gene_full_summary, get_scope_assignments, get_gene_assignment,
  update_gene_assignment, assign_curator_to_gene, get_available_genes_for_scope,
  update_precuration, approve_precuration, reject_precuration, delete_*,
  create/update_review_comment, execute_workflow_transition, get_methodology_version,
  validate_evidence_data, get_scoring_engine_info, search_hpo_terms, validate_hpo_term,
  get_inheritance_patterns, search_omim_diseases, get_omim_disease.
- The web UI (frontend/src/api) uses: ontology MONDO/OMIM search, get OMIM, HPO
  inheritance; HGNC search/fetch; /genes/resolve; validate PMIDs; validate-evidence;
  /curations/{id}/diff; detail=true on curations and schemas. It does NOT use:
  /publications/search, mentions_gene, GET /publications/{pmid}, ontology HPO search or
  HPO validate, /curations/{id}/review, POST /scopes/{id}/genes.

## Ranked removal / trim list
1. REMOVE search_pubmed (#510, unreleased). Owner: endpoints/publications.py
   `search_pubmed`; services/publication_service.py `search_term`, `SEARCH_SORTS`,
   `_search`, `search_publications`; schemas/validation.py `PublicationSearchHit/Response`;
   tests/api/test_pubmed_search.py; the pmid hint in mcp/audit.py `_NOT_FOUND_HINTS`.
   Effect: -1 tool, -1.2k chars of list, ~-200 lines. UI not affected. Make sure #518
   also drops its title/abstract gene filter, since it only serves this route.
2. REMOVE mentions_gene on validate_pmids (#510/#518, unreleased). Owner: publications.py
   lines ~109-113, `gene_names`, `mentions`, the `gene_symbol` field and `mentions_gene` in
   schemas/validation.py, tests/api/test_pmid_gene_mention.py. Why: it is a guess from the
   title and abstract only (cohort and functional papers often name the gene only in the
   full text), and it pushes agents to fetch abstracts. PubTator in GeneFoundry does
   this properly. Effect: ~-150 lines, a shorter validate_pmids description.
   validate_pmids itself stays (KEEP: confirms cited PMIDs exist; saves use the same code).
3. TRIM get_publication from the core set (and drop the batch/abstract reads in #518).
   It was the most-called tool in the study (111 calls), all for reading abstracts.
   REST stays on /mcp/full. Also drop the `validate_pmids` text in `_DESCRIPTION_EXTRAS`
   ("get_publication returns the abstract"). Effect: removes the biggest token sink
   in the study transcripts.
4. TRIM the ontology search tools from core: search_mondo_diseases, search_omim_diseases,
   get_omim_disease, search_hpo_terms, validate_hpo_term, get_inheritance_patterns.
   REST stays (MONDOAutocomplete, OMIMAutocomplete, HPOInheritanceSelect use it). ID
   validation stays: save/submit already check MONDO/OMIM/HP IDs
   (services/evidence_ids.py -> ontology_service.lookup_terms). Drop their `SLIM_KEYS`.
   Effect: -6 tools, -3.6k chars.
5. TRIM gene lookup to the two intake tools. KEEP add_genes_to_scope, resolve_genes,
   get_scope_genes. Remove from core: search_hgnc_genes, fetch_hgnc_gene, search_genes,
   get_genes_by_symbol, get_gene, get_gene_by_hgnc_id, create_gene, get_gene_full_summary.
   Update the gene hint in `_NOT_FOUND_HINTS` (it names create_gene). Effect: -8 tools,
   -5k chars. REST is untouched (UI uses HGNC search/fetch).
6. TRIM assignment tools that add_genes_to_scope replaced: bulk_create_gene_assignments,
   create_gene_assignment, get_scope_assignments, get_gene_assignment,
   update_gene_assignment, get_available_genes_for_scope. KEEP assign_curator_to_gene
   (a scope admin hands a gene to a curator). Remove the bulk hint in `_TOOL_HINTS`.
   Effect: -6 tools, -3.9k chars.
7. TRIM methodology and workflow extras: validate_workflow_transition (get_workflow_state
   already lists allowed moves and why the others are blocked), get_methodology_version,
   get_scoring_engine_info, validate_evidence_data (save returns the same warnings).
   KEEP get_workflow_state and execute_workflow_transition (backward moves).
   Effect: -4 tools, -2.2k chars.
8. TRIM inbox and invitation tools: list_notifications, mark_notification_read,
   invite_member, get_my_pending_invitations, accept_invitation. add_member covers MCP
   pipeline setup; read_my_work and get_my_review_assignments are the queue. Effect: -5
   tools, -3.4k chars (invite_member alone is the 2nd largest tool).
9. SHRINK instructions paragraph 4 (Literature) to two lines: "Research (papers,
   abstracts, genotypes, variants, MONDO/HPO lookup) comes from GeneFoundry; record the
   evidence here. validate_pmids confirms PMIDs; saves check PMID, MONDO, OMIM and HP
   IDs." Update the test in tests/api/test_mcp_toolsets.py:316 that pins the old wording.

Totals for items 1-8: 78 -> ~47 core tools; tools/list about -20k chars (~-35%, about
5-6k tokens per session); ~-350 lines of backend code and tests. REST used by the UI
stays. /mcp/full keeps every trimmed tool.

## KEEP (and why)
- Curation flow: create/get/list/update/save_draft/submit for precurations and curations,
  approve/reject_precuration, submit_peer_review, assign_peer_reviewer, get_peer_reviewers,
  read_curation_for_review (one call for the reviewer), curation_diff (what changed since
  the last review round), calculate_score, list_review_comments/create_review_comment,
  get_workflow_audit_trail, get_curation_schema with path= (12 calls per round, replaces
  reading whole schemas), get_workflow_pairs/get_workflow_pair, scope setup tools (#509).
- `_EVIDENCE_PATHS` on save_draft_curations (3.2k chars, the largest tool): it is what lets
  an agent save scored evidence without reading an example. Keep it on one tool only, as now.
- The 8k-token result cap (mcp/audit.py, ~15 lines): it only applies to tools that can be
  narrowed and turns a 30k-token dump into a clear error. Cheap, keep.
- Argument checks (`coerce_arguments`, `argument_errors`, ~70 lines): they stop a missing
  path argument from reaching the API as a literal "{item_id}" and name the wrong field.
  Keep; this is the input boundary.
- Per-resource hints: keep, but only for tools that stay in core. test_mcp_toolsets.py:290
  already fails if a hint names a tool that is not listed, so items 1, 5 and 6 will turn it
  red until the hints are fixed. Good.
- detail/compact defaults on REST (curations, schemas, scopes): the UI sends detail=true
  (api/curations.ts, api/schemas.ts), so lean defaults cost the UI nothing.
- PATs, LLM console/worker, evidence ID checks: owner-approved, not audited further.

## Risky to remove
- Ontology and gene tools (items 4, 5) assume GeneFoundry is connected next to Gene
  Curator. The study runs never called GeneFoundry; without it, an agent on /mcp cannot
  find a MONDO ID for a new precuration. Rerun one study round with GeneFoundry attached
  before you merge items 4 and 5.
- Do not delete the ontology, HGNC or /publications/validate REST routes: the web forms
  use them, and save/submit validation uses the same services.
- approve_precuration, reject_precuration and delete_* had 0 calls only because the study
  tasks never needed them. They are workflow tools; keep them.
- read_my_work and get_my_review_assignments overlap (both list what waits for my review).
  Merging them changes the instructions and both snapshots; leave it for a later wave.

Verdict: do items 1-3 inside #518 now (all unreleased), then items 4-8 as one CORE_TOOLS
edit plus the hint and snapshot updates, after one GeneFoundry-attached study round.
Lean: about -350 lines, -31 core tools, ~-20k chars per session; 0 dependencies.
Not checked: the LLM worker and PAT code, frontend views, Postgres tests; tools/list sizes
were measured on origin/master in a throwaway worktree, nothing else was run.
