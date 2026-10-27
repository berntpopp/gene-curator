# Wave 5 clinical scoring research and decision record

Date: 2026-10-22. Baseline: `origin/master` a7538d1 (v0.6.0).
Scope: #438 and #434. Read-only investigation; no product, snapshot, database or GitHub changes.
Method: Ponytail full; Academic Research Suite fact-check workflow; official PDF, current code,
existing tests and seven additional runtime assertions. Claude Opus 5.5 advice was obtained by
`wave5_plan`; its advice did not independently inspect the PDF and is advisory only.

## Verified clinical evidence

[ClinGen SOP v11, official PDF](https://www.clinicalgenome.org/site/assets/files/9851/gene-disease_validity_standard_operating_procedures-_version_11_docx.pdf)
was retrieved directly; printed page 17 was also rendered and inspected visually.

- Page 17: suggested starting points are 1.5 per null variant and 0.1 per other variant;
  ranges are 0–3 and 0–1.5 per variant, respectively. AR alleles are assessed independently.
- Pages 18–19: defaults assume qualifying evidence and the appropriate disease mechanism;
  expert judgment can reduce a score to zero.
- Page 20: sum in-trans allele contributions; double the assessed variant for homozygotes.
  Therefore two ordinary other variants suggest 0.2; two ordinary null variants suggest 3.
- Page 21: homozygous inherited nonsense explicitly gives 3. Mixed null/missense gives 1.6,
  rounded to 1.5 for GCI; another example caps homozygous nonsense with functional evidence at 3.
  Thus starting defaults, allele ranges, proband totals and GCI presentation are distinct.

This investigation intentionally targets v11, not the newer SOP version.

## #438 delegated decision: immutable successor, existing v1 retained

The owner delegated the decision and instructed end-to-end execution without questions.
After direct consultation with **Claude Code CLI `claude-opus-5-5`**, the orchestrator
accepted a narrow new immutable methodology version. Retaining the limitation alone is
not the selected resolution: the starting values are sufficiently established to fix.
This supersedes the preliminary retain-v1-only recommendation. Existing v1 snapshots,
curation pins and evidence remain unchanged; the correction applies to the successor.

The initial AR-other selector is **Null + Other**, so a universal 0.2 would be wrong.
Use this explicit starting-score policy, matching the existing variant selector:

| Table | Selector value | New starting score | Case rationale |
| --- | --- | ---: | --- |
| AR null | `two_null` | 3 | Two baseline null contributions |
| AR null | `null_and_null` | 3 | Homozygous null example |
| AR other | `null_and_other` | 1.5 | Choose the SOP's GCI-rounded mixed-case example |
| AR other | `two_other` | 0.2 | Two baseline other contributions |
| AR other | `homozygous_other` | 0.2 | Doubled baseline other contribution |

The numerical evidence above is from the verified PDF; this table specifies the project's
chosen starting-score policy, not automatic evidence adjudication.

### Smallest complete design (slice J, after G and F)

1. Publish a new immutable version for the built-in ClinGen methodologies, preserving all
   existing versions, pins and evidence. Assign the migration number in merge order, not
   now. Use the established snapshot/publish mechanism; update the matching working copies
   so subsequent publications retain the correction. Match only the intended stock schema
   and stock point model; do not rewrite user-customized or derived methodologies. Do not
   disable immutability triggers. Confirm newly created curations pin the successor.
2. AR null uses scalar points default 3. AR other keeps its existing selector and paths,
   with scalar default 1.5 plus a narrow field-schema `default_by` mapping: selector field
   `variant_type`, values as above. Pass this through the existing schema generator and
   frontend field types. Validate mapping shape, referenced selector/options, numeric finite
   values and column bounds at publication. Preserve scalar defaults for other schemas.
3. The generic evidence table resolves the mapping when adding a row. Maintain a temporary
   Set of automatically managed **new row IDs**; stable IDs already exist. Selector changes
   update points only for those rows. Any explicit points input removes the ID, even when
   the emitted number equals the previous number; do this before the equality early-return.
   Explicit zero, cleared values and all intentional manual edits remain untouched. Loaded
   rows never enter the Set. Clear tracking when rows are removed. No persisted provenance
   field, new allele model, watcher-driven reload updates, or equality-based overwrite.
4. Opt the successor's AR case types into `blank_at: null`: in this mode the existing case
   rule decides whether evidence exists after excluding the numeric score and row ID, as
   well as existing selector/status presets. Thus points alone, defaults, row IDs, or
   selector-only edits never score. A meaningful proband/variant/PMID/explanation can make
   the entered row count; then use its explicit numeric score, including zero. Implement
   this as a local branch; **do not globally change ID handling or numeric blank_at behavior
   for v1**. This removes the need for a duplicated selector-aware sentinel map. Validate
   the new null sentinel and preserve existing numeric sentinels. No automatic backend
   multiplication or replacement of stored scores.
5. Explain in schema help text that loaded/manually edited rows preserve their entered
   score when the variant selection changes, and curators must reassess that score. A
   separate Apply suggestion control is unnecessary for this scope.

### Required acceptance and verification

- Golden cases for all five selector values above, each with its stated per-case reason.
- New, untouched and selector-only rows, including generated IDs, score zero under v2.
- Numeric-only v2 rows score zero until evidence is entered; explicit zero with evidence
  stays zero; clearing/re-entering evidence gives consistent live and saved scores.
- New automatic rows follow selector defaults. Manual edits to zero, arbitrary values,
  cleared values, and the **same value as the suggestion** survive selector changes.
- Loaded rows emit nothing on mount/reload; changing their selector never replaces points.
  A loaded empty row stays unscored after such a change. Remove/re-add uses fresh tracking.
- New unpublished malformed default mappings are rejected with useful diagnostics.
- Real PostgreSQL API flow as app_user: publish/resolve successor, create a newly pinned
  curation, save/reload evidence, obtain equal live and persisted totals/traces; preserve
  D1 and scope isolation. Existing v1 curations remain pinned and calculate unchanged.
- Migration idempotent and self-recording; existing snapshots byte-identical; existing
  evidence and pins unchanged; custom models untouched; immutability still enforced.
- Browser re-check after merge: both AR tables, selector timing, same-value manual edit,
  save/reload, switching tabs and returning, untouched-row total, then narrow reruns after
  any fix. Complete normal CI and required PostgreSQL gates before merge.

### Remaining clinical boundaries

Mixed null/other is arithmetically 1.6, while the SOP's GCI example uses 1.5. We choose
**1.5 as the documented initial suggestion**, retaining manual 1.6; this is resolved policy,
not a blocker. Homozygous/consanguinity exceptions, supporting functional evidence,
uncertain phase and single-identified-allele exceptions still require curator judgment.
No automatic variant classification or phase adjudication is introduced. Existing range
caps stay unchanged: the page-21 example prevents inferring an AR-null cap of 6 simply
from per-allele ranges. Broader range changes are outside this default-only correction.

Actual Opus consultations are captured locally at
`/tmp/w5-clinical-opus438-answer.txt` and
`/tmp/w5-clinical-opus438-followup-answer.txt`. Opus read the PDF text extraction, not the
matrix image; the researcher independently verified the image. Its initial equality-based
overwrite and later global-ID-ignore suggestions were rejected as unsafe for manual scores
and v1 preservation, respectively.

## #434 implementation recommendation

1. Resolve the pinned scoring model before deciding which evidence keys recompute supports.
   Recognize its configured section/type paths and override inputs; retain meaningful skips
   and report truly unmapped evidence. Do not remove the safety guard wholesale. Preserve
   non-ClinGen skipping, pinned-version precedence, idempotency and class-change audit logs.
2. Choose the acceptance criterion's **explicit flag** option for out-of-range rows, rather
   than silently changing historic totals. Report the path, supplied value and pinned range;
   retain save/submit 422 checks. Cover negative, excessive and non-finite inputs. Reuse the
   range helper where suitable, accounting for its import dependency on the ClinGen engine.
3. Distinguish positive not-counted points from counted evidence in missing-PMID wording.
   Cover nested genetic and experimental evidence, legacy lists, malformed PMIDs and blanks.
4. Extend real PostgreSQL coverage to invoke `pg_temp.clingen_046` on both an old-template
   document and a custom model. Assert replacement of only the old template, preservation
   of the custom model, idempotency and immutable snapshots. Existing tests only exercise
   already-migrated state. Recompute changes also require an app_user API-created evidence
   flow; do not introduce any platform-admin RLS bypass.

No new migration or published-model mutation is needed for this #434 strategy.

## Validation performed

- `cd backend && uv run pytest tests/unit/test_point_model.py tests/unit/test_clingen_v1_correction.py tests/unit/test_clingen_pmid_warnings.py -q`: all 220 tests passed; deprecation warnings only.
- Seven direct baseline assertions passed, reproducing: unchanged 0.1 blank row scores zero;
  entered 0.1 scores 0.1; changing only the blank-row points to 0.2 makes it count; entered
  99 reaches the category cap rather than the row cap; a custom category scores normally but
  recompute rejects its key; positive not-counted points are mislabeled as scored.

Skipped here: PostgreSQL, browser flows and full CI, because this was a read-only research
assignment. Risk: existing v1 AR defaults can under-score qualifying evidence; automatic
recalculation cannot determine which stored values were intentional curator decisions.

## Appendix: finite LOD fallback discovered during slice F review

Investigated at `origin/master` 4fe8b6d on 2026-10-22. This is distinct from F's non-finite
number correction; F must not change valid finite mappings. Read source/call sites and
actual SOP PDF pp.28–35; rendered page 34 to inspect its formula and matrix. Consulted
actual `claude-opus-5-5` again; answer is `/tmp/w5-clinical-lod-opus-answer.txt`.

### Clinical finding

[Official SOP v11, pp.28–35](https://www.clinicalgenome.org/site/assets/files/9851/gene-disease_validity_standard_operating_procedures-_version_11_docx.pdf#page=28):
published LOD should not be re-estimated. Estimated LOD requires eligible pedigrees
(AD/XL at least four segregations; AR at least three affected individuals), suitable
penetrance/phenocopy assumptions and no unexplained non-segregation. AR estimation needs
affected/unaffected counts and parental-risk assumptions; the universal AD multiplier
cannot establish eligibility or represent AR pedigrees.

Figure 6 (p.34) maps **summed eligible-family LOD**, by sequencing method:

| Total LOD | Candidate gene | Exome/genome/whole linkage region |
| --- | ---: | ---: |
| <2 | 0 | 0 |
| 2–<3 | 0.5 | 1 |
| 3–<5 | 1 | 2 |
| ≥5 | 1.5 | 3 |

Mixed-method points weight these two coefficients by their respective LOD contributions,
then round to one decimal. Page 35's examples give 1.7 for candidate 1.5 plus comprehensive
2.8, and preserve 2 for comprehensive 3.1 rather than reducing it by including candidate
1.2. Eligibility, method, inclusion and aggregate information are essential; merely
replacing numeric thresholds remains incorrect.

### Confirmed application impact

- Nested evidence invokes `segregation_points`: the presence of a `points` key takes
  priority, including explicit zero, null and empty string. Only an absent key enables
  LOD/count fallbacks. The normal form supplies points=0, so ordinary UI rows do not use
  the automatic fallback. API/draft/imported rows without that key can use it.
- The nested automatic function applies 0.6/1.2/2.4 thresholds per row; counted segregations
  use the same AD multiplier without inheritance or eligibility inputs. Both are unsupported
  substitutes for the clinical procedure above and can increase classifications.
- Flat legacy lists follow a separate 3/5/7 heuristic, including a family-count estimate,
  and currently ignore entered segregation points. Correcting only the nested helper
  leaves this alternative automatic path in place.
- Calculation reaches persisted score updates, score previews, validation scoring and the
  recompute service through the shared ClinGen engine. The existing category cap of 3,
  genetic cap of 12 and total cap of 18 can conceal individual errors.
- The schema lacks sequencing method, qualifying-family status, published/estimated source,
  sufficient AR pedigree inputs, and an inclusion flag. Existing save/review guards do not
  reliably enforce the complete schema shape; validator-only rejection is insufficient
  protection against legacy-shaped evidence reaching the scorer.

### Selected J containment, preserving v1

The orchestrator approved the smallest safe successor behavior: **explicit curator-entered
segregation points only**, with clear missing-score feedback. Do not build automatic
pedigree interpretation in J. This is containment, not a claim to implement automatic SOP
segregation scoring.

- Choose an explicit-points rule in the successor's pinned segregation type (default zero),
  replacing the automatic segregation rule only there. Honor that pinned rule in both
  nested and flat-legacy segregation dispatch; never key behavior to a globally changed
  engine function or assume a version number. A plain rule deletion affecting only nested
  rows is incomplete. Existing numeric rules and all finite legacy v1 outputs remain as-is.
- When LOD/count evidence exists but `points` is absent, null or empty, return zero and an
  informative missing-score warning. Explicit numeric zero is an intentional assignment,
  not missing. Never manufacture points from LOD or family counts in the successor.
- Preserve all explicit, valid entered points and current category/section/total caps.
  Range/non-finite handling remains governed by F's checks. No rewrite of existing rows,
  snapshots, pins, golden expectations or stored historical totals.
- Schema help should explain that the curator assigns the segregation total after assessing
  all included families and methods; per-family automatic suggestions are not available.
  Persisted and live scoring must agree, including legacy evidence if it can reach the API.
- Full eligibility-aware, inheritance-aware, method-weighted aggregate LOD automation is a
  **separate follow-up feature** with a schema/clinical-model design, not a threshold patch.
  This recommendation does not defer the feasible explicit-points containment.

### Tests and case-by-case rationale

Keep current v1 finite golden cases unchanged. Add successor-specific cases:

| Input | Successor expectation | Rationale |
| --- | --- | --- |
| LOD 1.2, points missing | 0 + missing-score warning | No unsupported automatic conversion |
| LOD 3.1, points 2 | 2 | Preserve explicit curator assignment |
| LOD present, points 0 | 0, no missing-score warning | Zero is intentional |
| LOD present, points null or empty | 0 + warning | Missing score differs from zero |
| Count 3, points missing | 0 + warning | No unsupported count-to-score inference |
| Two assigned rows 2 + 2 | 3 category total | Existing category cap unchanged |
| Legacy segregation LOD 9, no points | 0 + warning | Legacy shape cannot bypass containment |
| Legacy segregation LOD 9, points 1 | 1 | Explicit score controls the successor |

Verify v1 nested threshold boundaries, explicit zero/null/empty behavior, count fallbacks,
legacy thresholds and family-count paths retain their finite results. Add real app_user
create/save/reload/preview checks for new and old pins, and warning/manual-zero browser
checks. Inspect each new golden case rather than regenerating expected values wholesale.

Five direct baseline assertions reproduced the missing-vs-cleared distinction and low-LOD
and low-count over-scoring. A read-only hypothetical nested explicit-only model comparison
found **33** existing golden records containing nested fallback inputs and **25** containing
legacy segregation. Of the nested records, **19 totals and 10 classifications** would change
under that hypothetical model; caps mask the other differences. These are synthetic test
records, not production prevalence, and not approval to alter historical expectations.

The ten synthetic classification changes (golden JSONL line → old/new) were:
33: Strong→Moderate; 57: Strong→Moderate; 85: Limited→No known;
91: Strong→Moderate; 98: Moderate→Limited; 109: Moderate→Limited;
121: Moderate→Limited; 133: Moderate→Limited; 136: Moderate→Limited;
155: Moderate→Limited. Their rationale is removal of unsupported automatic contributions;
their original v1 expectations must remain unchanged.

### Scope cross-check and limits

Checked the current issue-title inventory against every excluded issue. The relevant
excluded #386 concerns engine dispatch/RLS, not this LOD algorithm; its body confirms the
distinction. Closed #157 concerns case-control/classification disagreement; #266 describes
the general interpreter but has no dedicated segregation acceptance. No existing dedicated
LOD/segregation issue appeared in the inventory. The full-automation follow-up still needs
to be filed by the orchestrator; this research did not alter GitHub.

No product edits or PostgreSQL/browser/full-CI runs were made for this appendix. Historical
v1 automatic segregation can remain clinically inflated; preserving it avoids unauthorized
reinterpretation but requires explicit reporting and eventual reviewed migration, not a
claim that the old automatic scorer is SOP-conformant.

### Implementation follow-up (J)

Full eligibility/family/method-aware segregation automation is now tracked separately in
[#447](https://github.com/berntpopp/gene-curator/issues/447). Issue inventory was checked
for segregation, LOD and pedigree duplicates before filing. J implements only the approved
explicit-points containment in an immutable successor, with migration number 049 assigned
by the orchestrator. Direct PDF text and matrices on printed pp.17/34 were rechecked.

### Browser-found assignment distinction (successor-only correction)

The candidate browser exposed a missing field-default change: inherited segregation points.default=0 made a new untouched row indistinguishable from a deliberate curator zero. The successor now declares points.default=null in unpublished migration049. Historical v1 snapshots/default0 and all saved rows remain unchanged. Rationale: an untouched UI starting value is not a curator assignment; LOD/count input with null points must produce0 plus the missing-score warning, while explicit manual0 suppresses that warning. No global zero heuristic or provenance model was added.

Correction6fbddc4 has three regression-first fresh-Postgres cases (old/new field-default distinction and nested/legacy actual app_user save/preview/reload). All15 J PostgreSQL cases and10 table tests pass. Browser must run on a fresh migration stack; existing published test snapshots are never edited. Full CI and independent narrow browser confirmation are pending at this checkpoint.
