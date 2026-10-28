# MCP token-efficiency plan (Claude Code first), 2026-10-27

Inputs: round-2 transcripts (20 Claude runs, master 96caca15), 3 new feedback sessions on the study stack
(`token-sessions/claude/{A,B,C}`, $0.73, PATs revoked), web research, fleet standards. Measurement script:
`runner/tokens.py` (one result costs its tokens once per later request; ToolSearch loads use the measured
context delta). In flight and not re-proposed: W7M4-W7M7 (see "In flight: enough?").

## 1. Where the input tokens go (round 2, 1.97M input tokens, 134 model requests)

The protocol metric "tool list = 5.3% of input" counts the list once. Claude Code resends it on every model
request, so it is the single largest sink. Every request also resends all earlier results, so **requests
per task are the multiplier for everything else.**

| Sink | Size | Frequency | Share of input | Notes |
| --- | --- | --- | --- | --- |
| Deferred tool-name list (186 names + ToolSearch) | 4.4k tok | every request (6/task median) | **29.5%** | A/B baseline `round-2/baseline.json`; 41-49% on short tasks (T0, T3, T4) |
| Rest of base prefix (Claude Code system, prompt, runner schema) | 3.8k tok | every request | 26% | not product; W7M4 adds ~0.6k instructions here |
| Tool schemas loaded via ToolSearch | 324 tok/tool, 159 loads, 1.85 searches/run | stay for the rest of the run | **16.4%** | 51.5k tokens loaded once, 324k cumulative |
| Tool results (all tools) | 3.1 KB avg | 115 calls | 13.7% | but each is a 1h cache write (2x price), so they drive cost |
| Model's own turns (thinking, tool inputs e.g. evidence_data) | - | - | ~14% | merge-patch (W7M7) shrinks save inputs |

Top result sinks (cumulative input tokens over round 2; bytes are per call):

| Tool | Calls | Avg bytes | Max bytes | Cum. tokens | What was not needed (agent quotes, sessions A-C) |
| --- | --- | --- | --- | --- | --- |
| get_curation_schema (full) | 4 | 7.8k | 13.9k | 50k | "Only field_definitions plus the regex patterns"; compact=true is 1.8 KB but not default |
| list_scopes | 9 | 2.3k | 3.4k | 39k | "Only the id and default_workflow_pair_id for the scope named study-r2-1" (W7M5) |
| get_curation | 11 | 3.9k | 5.2k | 38k | "Full computed_scores trace and audit fields when I only fetched it to learn the evidence_data shape" |
| get_json_schema_for_schema | 2 | **25.6k** | 25.6k | 32k | largest result of the round (T5b); `enumOptions` duplicates `enum` with UI labels |
| list_members | 5 | 1.7k | 1.7k | 16k | invited_by, team_id, orcid, email, username = full_name per row |
| list_curations / list_precurations | 8 / 4 | 1.0k / 3.8k | 2.9k / 5.5k | 12k / 11k | B: `pending_review=true` returned 10 rows, "9 of them were already approved" |
| save_draft_curations / submit_curation | 4 / 2 | 4.1k / 4.7k | 4.7k | 11k / 6k | "echoed full evidence_data plus the complete scoring trace including ~15 zero-item type entries" (W7M5) |
| validate_pmids, search_mondo_diseases | 4 / 2 | 1.1k / 2.4k | 2.4k | 7k / 7k | "Only is_valid, title, year"; "Only mondo_id and label" |

No identical read was repeated within a run; the waste is extra lookups, not re-reads. Per-task medians:
T0 27k, T1 89k, T2 207k, T2b 221k, T3 53k, T4 54k, T5a 44k, T5b 107k, T6 76k; all-task median 82.7k input,
12.3k cache-write tokens, 6 requests.

Calls the agents said they would skip (sessions A-C; same pattern in round-2 T2/T2b tool sequences):
- `list_scopes` only to turn a team name into an id (first call in 7/8 tasks, 11 calls).
- `get_peer_reviewers`/`list_members` only to turn "Bob Jones" into a UUID, then a separate `assign_peer_reviewer`
  after every submit (A, C, all T2/T2b): "submit_curation accepting a reviewer_id to submit-and-assign in one call".
- Gene entry: `get_genes_by_symbol` -> `search_hgnc_genes` -> `create_gene` -> `create_gene_assignment` per gene;
  T2-1 spent 10 of 19 calls here (3 failed `create_gene`, 3 `get_gene_by_hgnc_id`).
- `get_curation` only for `lock_version` before an edit ("Include lock_version in list_curations rows"), and on a
  *different* curation (NPHP1) only to learn the evidence_data shape.
- `get_precuration` to read evidence before approving (B): list rows lack a summary.

## 2. What the sources say (and where they conflict with our rules)

- Claude Code (v2.1.312 here) defers MCP tools: "Only tool names and server instructions load at session start";
  instructions and upfront descriptions are cut at 4,096 chars, deferred descriptions at 16,384; search "reads
  only the part within the shorter limit, so put the words Claude would search for near the start". Output
  warning 10k tokens, cap 25k (`MAX_MCP_OUTPUT_TOKENS`), text over 50k chars goes to a file;
  `_meta["anthropic/alwaysLoad"]` pins a tool. https://code.claude.com/docs/en/mcp
- Anthropic, Writing tools for agents: consolidate multi-step operations into one tool, filters and sane defaults,
  semantic names over UUIDs, `response_format` concise 72 vs detailed 206 tokens.
  https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic, Context engineering: "minimal viable set of tools", bloated tool sets are a common failure.
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Tool search docs: accuracy "degrades once you exceed 30-50 available tools"; keep 3-5 most-used non-deferred.
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool ; Advanced tool use (Opus 4
  49%->74%, 85% fewer definition tokens) https://www.anthropic.com/engineering/advanced-tool-use
- OpenAI: "Aim for fewer than 20 functions available at the start of a turn".
  https://developers.openai.com/api/docs/guides/function-calling ; Codex `enabled_tools`/`output_token_limit`.
- MCP spec 2026-07-28: tool lists "MUST NOT vary per-connection" but "MAY vary by the authorization presented on
  the request"; deterministic order for prompt-cache hits; `cacheScope: private`; text copy of structured content
  still SHOULD. https://modelcontextprotocol.io/specification/2026-07-28/changelog
- FastMCP 3.x: `Tool.from_tool`/`ArgTransform(default=..., hide=...)` change MCP-side defaults without touching
  REST; `ResponseLimitingMiddleware`; tags and visibility. https://gofastmcp.com/servers/transforms/tool-transformation
  , https://gofastmcp.com/servers/middleware ; docs advise against "mirroring your API to LLM clients".
- GitHub MCP server: `--toolsets` with a `default` set and `fields` params "to reduce response size".
  https://github.com/github/github-mcp-server ; Cloudflare code mode: 2,500 endpoints 1.17M -> ~1k tokens with
  `search()`/`execute()`. https://blog.cloudflare.com/code-mode-mcp/
- Fleet: `genefoundry-router/docs/TOOL-SURFACE-BUDGET-STANDARD-v1.md` (B1 1,200 tok/tool, B2 10k/server; our eager
  surface is 51k), `RESPONSE-ENVELOPE-STANDARD-v1.md` section 3 ("Omit, don't null-pad", compact default, 25k
  soft cap), `hgnc-link` `response_mode="compact"` default.

Conflicts with our rules, resolved:
- Parity: hiding tools must not remove capability. Role-filtered listing is allowed by the spec and hides only
  tools the caller would get 403 on; a "core" default keeps a full endpoint (owner decision, change 1).
- No per-user caching: only client-side prompt caching applies; keep tool order deterministic, no server cache.
- Router `search_tools`/`call_tool` and code mode: not adopted. Claude Code already defers; a gateway hides
  per-tool annotations and per-tool permissions (destructive confirmations), and code mode runs agent code
  server-side with the user's token. Revisit only if Codex returns without native tool search.
- `response_format` on all 186 tools: no; lean defaults on the dozen hot tools give the gain.

## 3. Ranked changes (impact on tokens per task x effort)

| # | Change | Owning files | Evidence | Expected saving |
| --- | --- | --- | --- | --- |
| 1 | **Smaller tool list.** (a) `tools/list` filtered by the caller's authorization: drop routes that need `get_current_admin_user` for non-admins (~40: llm-admin 17, logs 7, user admin, schema/pair authoring, cache stats, health). Calls stay routable (API answers 403). (b) Owner decision: `/mcp` serves a curation core (~70-80 tools: scopes, members, genes, assignments, pre/curations, workflow, review, evidence, ontology, PMIDs, my-work, notifications); `/mcp/full` (or `?toolset=all`) serves everything for parity. Use FastMCP tags already on every tool. | `backend/app/mcp/server.py` (list middleware or second FastMCP over same spec), `audit.py`, `backend/app/main.py` mount, `docs/MCP_CONNECTION_GUIDE.md`, `tests/api/test_mcp.py` snapshot per profile | 29.5% of input; 4.4k tok x 6 requests/task; Anthropic 30-50 tool degradation, OpenAI <20 | (a) ~0.9k tok/request (~6%); (a+b) ~2.5k/request, **~15-18% of input** |
| 2 | **Fewer round trips on the curation path** (each removed request saves ~10-25k input in T2/T2b): (a) accept `scope_name` wherever `scope_id` is required (list_precurations, create_gene_assignment, create_precuration, get_peer_reviewers); (b) optional `reviewer` (id or email) on `submit_precuration`/`submit_curation` that also assigns the reviewer, and email on `assign_peer_reviewer`; (c) add genes to a scope by HGNC symbol in one call (resolve + create if missing + assign, returning local gene ids); (d) `lock_version` in list_curations/list_precurations rows and the child `curation_id` on approved precurations; (e) `list_precurations(pending_review=true)` returns only submitted/in_review rows. All are REST params too, so parity holds. | `endpoints/precurations.py`, `curations.py`, `workflow.py` (assign), `gene_assignments.py`, `scopes` lookup helper in `crud/`, `schemas/` | 11 list_scopes calls; get_peer_reviewers+assign after every submit (A, C, all T2/T2b); T2-1 10/19 calls on gene entry; B got 9 stale rows | T2 11->7 requests, T2b 11->8: **~30-35% on T2/T2b**, ~1 request on most other tasks |
| 3 | **Lean MCP output, centrally.** In `ToolAuditMiddleware`, before text serialisation: drop `null`, `{}` and `[]` values and audit-only keys (`created_by`, `updated_by`, `submitted_by`, `approved_by`, `auto_saved_at`, `record_hash`, `previous_hash`, `methodology_version_id`) unless the tool was called with `detail="full"`; keep `false`, `0` and every id/name/status/lock field. MCP-only, REST unchanged. Add a hard cap: result over 8k tokens returns a typed `response_too_large` with the narrower call to make (no silent truncation). | `backend/app/mcp/audit.py`, test in `tests/api/test_mcp.py` | get_curation 10+ null/empty keys of ~40; fleet "Omit, don't null-pad"; Claude 10k warning | 15-25% of every result; results are 14% of input but most of cache writes |
| 4 | **MCP-side defaults on the heavy reads** via `ArgTransform` in `_annotate` (REST defaults unchanged): `get_curation_schema(compact=True)`; `get_json_schema_for_schema` excluded from MCP or compact (drop `enumOptions`); `search_mondo_diseases`/`validate_pmids`/`list_members` return id+label/title/year/role+name by default, full on `detail="full"`; list `limit` default 20. | `backend/app/mcp/server.py`, `endpoints/ontology*.py`, `publications.py`, `scope_memberships.py`, `validation.py` | 25.6 KB max result (T5b); full schema 13.9 KB vs compact 1.8 KB (A); agent quotes table 1 | max result 25.6 KB -> <8 KB; ~25k cumulative tokens on T2b/T5b |
| 5 | **Leaner loaded tool definitions.** In `_annotate`: strip `title` from inputSchema properties, integer bounds as ints, drop the "Destructive or irreversible: confirm..." prefix (destructiveHint carries it; keep one line in instructions); lead every description with search words (domain nouns) within the first 200 chars; `dereference_schemas=False`. | `backend/app/mcp/server.py`, snapshot test asserting median and max definition size | 324 tok/loaded tool, 16.4% of input; Claude search reads only the first part; fleet B1 | ~30% of loaded schema tokens, **~5% of input** |
| 6 | **Document the evidence_data paths** where they are needed: `save_draft_curations` description lists the scored paths and item fields for the default pair (or points to `get_curation_schema(compact=True)`), so no example curation is fetched. | `endpoints/curations.py` docstring, W7M4 instructions | C fetched NPHP1 curation (2.5 KB) for the shape; T2b fetched the 13.9 KB schema | 1 request + 2-14 KB per curation task |

Not now: `anthropic/alwaysLoad` on 3-5 entry tools (saves ~1 ToolSearch round trip but adds ~1.5k per request;
W7M4 instructions naming the tools should let the agent load all in one `select:`; re-check after round 3);
shorter client server name (`mcp__gc__` saves ~0.5k/request, but renames tools for existing users; docs note only).

## 4. In flight: enough?

- W7M4 instructions: ~2.4 KB, under the 4,096-char cap, but ~0.6k tokens on every request; keep it under ~2.5 KB
  and start each paragraph with search words. Text-only results help Codex; for Claude the gain is unverified
  (docs do not say whether both copies reach the model). Description cleanup is needed but not sufficient (change 5).
- W7M5 compact `list_scopes` + name filter shrinks the result but keeps the call; change 2a removes it. Concise write
  responses must cover precuration writes too (A: "create_precuration ... echoed the full evidence_data").
  Default `precuration_schema_id` (seen on `fix/mcp-study-responses`) removes `get_workflow_pair`: good.
- W7M7 merge-patch saves cut the model's own resent evidence_data (part of the ~14% "own turns").
- Nothing in flight touches the tool-name list (largest sink) or round trips for reviewer/gene entry.

## 5. Round-3 targets and how to verify

Measure with `python3 runner/tokens.py round-3` on the same tasks, Claude Code 2.1.312, `claude-opus-5-5`,
2 runs per task; report the tool-list share **per request** (round-2 SUMMARY divided 4.4k by the median input once).

| Metric | Round 2 | Round 3 target |
| --- | --- | --- |
| Median input tokens per task (all tasks) | 82.7k | <= 55k |
| T2 / T2b median input tokens | 207k / 221k | <= 130k / <= 140k |
| Median model requests per task (T2, T2b) | 6 (11, 11) | <= 5 (<= 7, <= 8) |
| Tool-list share of input (names x requests / input) | 29.5% | <= 15% |
| Visible tools for a curator token | 186 | <= 80 (core) or <= 146 (role filter only) |
| Largest tool result | 25.6 KB | <= 8 KB; p95 <= 4 KB |
| Median loaded tool definition | ~324 tok | <= 200 tok |
| ToolSearch calls per run | 1.85 | <= 1.3 |
| Median cache-write tokens per task | 12.3k | <= 9k |
| Success / unsafe | 17/20, 0 | no lower, 0 |

Gate checks before the round (no agent needed): `tools/list` as alice and as admin (count, bytes, per-tool
token estimate) in `test_mcp.py`; a snapshot test asserting the role filter and the size budgets in changes 3-5.

Skipped / not checked: exact admin-only route count (FastAPI lazy routers hid dependencies from a quick probe;
derive it from route dependencies in the implementation); Codex not measured; token estimate for non-ToolSearch
results uses bytes/3.2.
