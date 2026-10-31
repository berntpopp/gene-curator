# Segregation scoring spec (issue #447)

Source: ClinGen Gene-Disease Validity SOP v11
([PDF](https://www.clinicalgenome.org/site/assets/files/9851/gene-disease_validity_standard_operating_procedures-_version_11_docx.pdf)),
pp.28-35 read in full (text and rendered images, including the image-only formulas, Figure 5 and
pedigrees A-E), plus the segregation row of Figure 2 on p.17. Page numbers are the PDF's printed
page numbers. Quotes are verbatim. **OPEN** marks a point where the SOP is silent or ambiguous and
a clinical decision is needed before implementation.

## 0. Today and rollout

- Pinned v1 ClinGen models score segregation with legacy LOD fallbacks
  (`backend/app/scoring/clingen.py`: `lod_to_points_sop11` 0.6/1.2/2.4 thresholds,
  `legacy_lod`); the Wave 5 successor (`clingen_successor.py`) requires curator-entered points.
  The generic point model offers a `step` rule (`docs/POINT-MODEL.md`), which sums one field with
  no eligibility or method weighting.
- None of these match Figure 6. The behaviour below ships only as a **new immutable bundle
  version**. Old pins keep their engine and are never rescored (issue #447).

## 1. Family eligibility

### 1.1 Published LOD (pLOD)
- "This LOD score should be documented and may be used to assign segregation points (according to
  the sequencing methods ...)" (p.28).
- "If a LOD score is provided by the authors, the ClinGen curator should not use the formula(s)
  below to estimate a new LOD score." (p.28) A pLOD row never gets an eLOD.
- "If for some reason you do not agree with the published LOD score, do not assign any points and
  discuss the concerns with the expert reviewers." (p.28) Disputed pLOD: family excluded, 0.
- **OPEN-1:** The size thresholds (1.2) are stated under the eLOD heading. The p.33 note says "LOD
  scores from all families meeting size requirements must be summed". Whether a pLOD family must
  also meet the size thresholds is not stated. A pLOD may also cover several families at once; the
  SOP does not say how to record that.

### 1.2 Estimated LOD (eLOD) preconditions (p.28)
Curators may estimate only if all hold:
- "The disorder is rare and highly penetrant."
- "Phenocopies are rare or absent."
- AD/XL: "calculated using ONLY families with 4 or more segregations present. The affected
  individuals may be within the same generation, or across multiple generations."
- AR: "ONLY families with at least 3 affected individuals in the pedigree, including the proband).
  Genotypes must be specified for all affected and unaffected individuals counted; specifically,
  parents of affected individuals must be genotyped or other methods must be used to show that the
  variants are in trans if the affected individuals are noted to be compound heterozygotes."
- "Families included in the calculation must not demonstrate any unexplainable non-segregations
  (for example, a genotype-/phenotype+ individual in a family affected by a disorder with no known
  phenocopies)."
- "If any of the previous conditions are not met, do not use the formula(s) below" (p.29).
- **OPEN-2:** The SOP uses HCM, a reduced-penetrance disorder, as its eLOD example (Pedigree A,
  p.31; Example 1, p.34) while requiring "rare and highly penetrant". Whether the first two
  preconditions are recorded once per curation or per family is not stated.

### 1.3 Who counts (phenotype-positive and phenotype-negative)
- AD/XL: "only affected individuals (genotype+/phenotype+ individuals) or obligate carriers
  (regardless of phenotype) should be included" (p.29). An obligate carrier is "inferred to carry
  the variant by virtue of their position in the pedigree" (p.29).
- Genotype+/phenotype- relatives in AD/XL are not counted and do not disqualify the family when
  delayed onset or reduced penetrance explains them: "the absence of a phenotype in two genotype+
  individuals (III-2 and III-5) is considered irrelevant ... However, these individuals are not
  included in the eLOD calculation because they are unaffected." (p.31)
- Segregations = "the number of affected individuals minus one, the proband, to account for the
  proband's genotype phase being unknown. However, as there may be exceptions, segregations should
  be counted carefully" (p.31).
- AR unaffecteds: "count unaffected individuals as those who would be at the same risk to inherit
  two altered alleles as an affected individual, i.e., homozygous normal or heterozygous carrier
  siblings of a proband" (p.32). "Parents are not typically counted in the eLOD calculation" (p.32).
- AR homozygous proband: "variant phasing is not required" (p.32). Compound heterozygous proband:
  "it is recommended that variants be phased. For example, at a minimum, at least one parent must
  be genotyped" (p.32). The p.28 bullet is stricter ("must be genotyped or other methods must be
  used to show that the variants are in trans"); the engine follows p.28.
- Twins: "dizygotic (fraternal) twins count as two separate individuals and monozygotic
  (identical) twins count as one individual" (pp.29-30).
- **OPEN-3 Consanguinity:** pp.28-35 do not mention consanguinity. (p.20 mentions it only for
  case-level points of homozygous variants.) No segregation rule exists for it.
- **OPEN-4:** Pedigree E (p.33) shows two genotype aa siblings drawn unaffected; the SOP excludes E
  only because it "does not have enough affected individuals" (p.32). Whether genotype+/phenotype-
  siblings in an AR family count as unaffected, or as a non-segregation, is not stated.

## 2. Inheritance and LOD formulas (θ = 0, p.28)

| Model | Formula (p.30-31) | Note |
| --- | --- | --- |
| AD / XL | Z = log10(1 / 0.5^Segregations) | "assuming a carrier mother, not an affected father" (p.30) |
| XL, affected father | base "should be changed to '1' for any daughters" (p.30) | each such daughter adds log10(1) = 0 |
| AR classic (both parents carriers) | Z = log10(1 / (0.25^(Affected-1) · 0.75^Unaffected)) | Figure 5 table (p.31) |
| AR, one parent affected, other carrier | Z = log10(1 / (0.5^(Affected-1) · 0.5^Unaffected)) | CRADD/Harel 2017 (p.31) |
| Other pedigrees | "adjust the base numbers in the equation above to reflect the risk of inheritance" (p.30) | no table; "do not rely on the table below (Figure 5)" (p.31) |

- Figure 4 (p.30), AD/XL, 4 to 15 segregations: 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9,
  4.2, 4.5 (that is, 0.3 per segregation).
- Figure 5 (p.31), AR, rows = affected 3-10, columns = unaffected 0-10. Row 3: 1.20, 1.32, 1.45,
  1.50, 1.70, 1.82, 1.95, 2.07, 2.20, 2.33, 2.45.
- **OPEN-5 Precision:** Figures 4 and 5 show rounded values (4 × log10 2 = 1.204 is shown as 1.2).
  Figure 5 is not rounded consistently: (3,1) = 1.329 is shown as 1.32, but (4,2) = 2.056 is shown
  as 2.06. Example 2 uses 1.5/1.3/1.5 where p.32 used 1.45/1.32/1.45. Proposal: compute exact
  values, sum them, display 2 decimals. This needs a decision because results near a band edge
  depend on it.
- **OPEN-6:** Whether daughters of an affected father (who add 0 LOD) count toward the AD/XL
  "4 or more segregations" minimum is not stated.
- **OPEN-7:** Inheritance modes other than AD, XL and AR (for example mitochondrial or
  semidominant) are not covered.
- "Expert reviewers may choose to specify ... more formal, rigorous LOD score calculations" (p.30).
  The engine accepts these as a curator-entered LOD (`lod_formula = adjusted`).

## 3. Sequencing method categories (p.33)

- Candidate gene: "a candidate gene approach in which only one or a handful of genes in a linkage
  region are sequenced".
- Comprehensive: "exome/genome sequencing was performed or if the entire linkage interval was
  sequenced". Figure 6 calls this column "Exome/genome or all genes sequenced in linkage region".
- "Segregation implicates a locus in a disease, NOT a variant" (p.30). The curator must "evaluate
  the methods used to identify candidate variants" (p.33).
- **OPEN-8:** Gene panels or partial-interval sequencing (more than "a handful" but not the whole
  interval) are not classified.

## 4. Summation, Figure 6 and the weighting formula

- "if more than one family meets the criteria above for scoring segregation information, the LOD
  scores are summed" (p.30). "LOD scores from all families meeting size requirements must be summed
  before awarding segregation points, regardless of the sequencing methodology used." (p.33)
- **Figure 6 (p.34)**, total summed LOD across all families:

| Total LOD | Candidate gene | Exome/genome or all genes in linkage region |
| --- | --- | --- |
| 0-1.99 | 0 | 0 |
| 2-2.99 | 0.5 | 1 |
| 3-4.99 | 1 | 2 |
| ≥ 5 | 1.5 | 3 |

- **OPEN-9:** The bands leave gaps (1.99 to 2, 2.99 to 3, 4.99 to 5). Proposal: half-open bands
  [0,2), [2,3), [3,5), [5,∞) on the exact sum.
- Mixed methods (p.34): **points = (A/(A+B))·C + (B/(A+B))·D**. A is the summed LOD of candidate
  families, B is the summed LOD of comprehensive families, and C and D are the Figure 6 candidate
  and comprehensive points "within the range of the total summed LOD score (A+B)". "The points are
  rounded to the nearest 0.1 point." With one method only, the formula reduces to that column.
- **OPEN-10:** The tie-breaking rule for rounding (0.75 to 0.7 or 0.8, and so on) is not stated.
- **Max:** Figure 2 (p.17) gives segregation "0-3 points", "Max Score 3 points". The formula cannot
  exceed D ≤ 3.
- Advisory language: "simply having a single family meeting the minimum size requirements is not
  necessarily enough to warrant any points", and "the suggested points in Figure 6 are merely a
  guide" (pp.33, 35). **OPEN-11:** Whether the curator may override the computed points (with
  rationale), as the successor model allows today, needs a decision.

### 4.1 Omitting lower-quality candidate evidence (p.35, "Additional logic")
"For Family 1, an estimated LOD score of 3.1 is obtained from a study involving exome sequencing.
For Family 2, a candidate gene analysis was performed, and a LOD of 1.2 was estimated. ... 2 points
could be awarded for Family 1 alone ... If the second piece of evidence were to be included, the
points would be reduced to 1.8. In this situation, the formula should not be applied and the
maximum number of points (i.e. 2) should be given. The candidate LOD case can still be entered, but
do not check the 'Score?' box in order to exclude it from the final calculation."

- Engine rule: compute `formula_points` over the scored families. Also compute
  `comprehensive_only = Fig6_D(B)`. Final points = max(formula_points, comprehensive_only). When the
  maximum comes from `comprehensive_only`, the candidate families are reported as `omitted_lower`
  (still listed, not counted), which matches the GCI's unchecked "Score?" box.
- **OPEN-12:** The SOP text says 1.8, but the formula gives (1.2/4.3)·1 + (3.1/4.3)·2 = 1.72, which
  rounds to 1.7. The outcome (2 points) is the same either way. Whether the rule also applies in
  other cases (for example, dropping only some of the candidate families) is not stated.
- The per-family "Score?" checkbox (`scored`) stays curator-controlled.

## 5. Exclusions (a family contributes 0 and is listed with a reason)
1. pLOD disputed by the curator (p.28).
2. eLOD family where a precondition fails: the disorder is not rare and highly penetrant, or
   phenocopies are not rare (p.28).
3. AD/XL eLOD with fewer than 4 segregations (p.28).
4. AR eLOD with fewer than 3 affected individuals including the proband, counted genotypes not all
   specified, or compound heterozygous variants not shown to be in trans (p.28, p.32).
5. Unexplained non-segregation (p.28).
6. Curator unchecked `scored`, or the family was omitted by rule 4.1 (p.35).
7. Missing citation (existing citation policy, not SOP-specific).

## 6. Worked examples

SOP examples:

| # | SOP | Input | Expected |
| --- | --- | --- | --- |
| S1 | Pedigree A, p.31-32 | AD HCM; 4 segregations from proband III-1, counting untested obligate carrier II-2; genotype+ unaffected III-2 and III-5 not counted | eLOD 1.2 (exact 1.204) |
| S2 | X-linked pedigree, p.29 | II-4 is an obligate carrier "between two affected" (I-1, III-5); II-2 and III-6 are carriers | counted regardless of phenotype |
| S3 | Twins, p.29-30 | proband + 2 affected DZ twins with variant / + affected MZ twin | 2 segregations / 1 segregation |
| S4 | Summing, p.30 | Family A eLOD 1.2 + Family B eLOD 1.8 | total 3.0 |
| S5 | Pedigrees B, C, D, E, p.32-33 | AR hearing loss. B: 3 affected, 2 unaffected → 1.45. C: 3, 1 → 1.32. D: 3, 2 → 1.45 (II-2/II-3 drawn as twins, each counted). E: 1 affected | total 4.22; E excluded ("not enough affected individuals") |
| S6 | Example 1, p.34 | AD HCM, 11 affected = 10 segregations → LOD 3 (Fig 4); all 15 genes in the interval sequenced | comprehensive, 3-4.99 → **2 pts** |
| S7 | Example 2, p.35 | B 1.5 WES, C 1.3 WES, D 1.5 candidate (single gene). A=1.5, B=2.8, total 4.3, C=1, D=2 | 0.349 + 1.302 = 1.65 → **1.7 pts** (exact values 1.45/1.32/1.45 also give 1.7) |
| S8 | Additional logic, p.35 | F1 eLOD 3.1 exome; F2 eLOD 1.2 candidate | formula 1.7 (SOP text: 1.8, OPEN-12) < comprehensive-only 2 → **2 pts**, F2 `omitted_lower` |
| S9 | Adjusted AR, p.31 | CRADD (Harel 2017), one parent affected | use the 0.5/0.5 formula; no numbers given |

Boundary cases derived from the rules (exact LOD, half-open bands):

| # | Input | Expected |
| --- | --- | --- |
| T1 | AD, 3 segregations (0.903), exome | excluded (needs ≥ 4); **0 pts** |
| T2 | AD, 6 segregations (1.806) + AR 3 affected, 0 unaffected (1.204), both candidate | sum 3.01 → **1 pt**; the same families with exome → **2 pts** |
| T3 | AD 4 segregations candidate (1.204) + AD 4 segregations exome (1.204) | sum 2.408, C=0.5, D=1 → 0.25 + 0.5 = 0.75 → **0.8** (round half up; OPEN-10) |
| T4 | AD 10 segregations exome (3.010) + pLOD 2.0 exome | sum 5.01 → **3 pts** (the maximum); adding a further family stays at 3 |
| T5 | AR compound heterozygous, 4 affected, no parent genotyped and no phasing; plus pLOD 3.5 marked disputed | both excluded → **0 pts** with two reasons |

## 7. Implementation

New point-model rule `"rule": "segregation_sop11"` on the segregation family table, shipped in a
new ClinGen bundle version only. Earlier rule types are untouched.

### 7.1 Family-table fields

| id | type | allowed / note |
| --- | --- | --- |
| `family_label` | string | required |
| `pmid` | string | existing citation policy |
| `inheritance` | enum | `AD`, `XL`, `AR` |
| `lod_source` | enum | `published`, `estimated` |
| `published_lod` | number | when `published` |
| `published_lod_disputed` | boolean | default false; true → excluded |
| `lod_formula` | enum | `ad_xl`, `ar_classic`, `ar_one_parent_affected`, `adjusted` (when `estimated`) |
| `segregations_counted` | integer ≥ 0 | AD/XL: affected genotype+ plus obligate carriers, minus proband, MZ twins once, daughters of an affected father add 0 |
| `affected_count` | integer ≥ 0 | AR, including proband |
| `unaffected_count` | integer ≥ 0 | AR at-risk siblings only, parents excluded |
| `adjusted_lod` | number | when `lod_formula = adjusted`; requires `notes` |
| `genotypes_complete` | boolean | AR: all counted individuals genotyped |
| `compound_het` | boolean | AR |
| `in_trans_shown` | boolean | required true when `compound_het` |
| `unexplained_non_segregation` | boolean | true → excluded |
| `sequencing_method` | enum | `candidate_gene`, `comprehensive` (exome/genome or whole linkage interval) |
| `scored` | boolean | default true (GCI "Score?") |
| `notes` | string | free-text rationale |

Section-level booleans for the eLOD preconditions: `disorder_rare_highly_penetrant`,
`phenocopies_rare` (scope per OPEN-2).

### 7.2 Per-family rationale string

`"<family_label> (PMID <pmid>): <inheritance>, <pLOD|eLOD> <lod:.2f> [from <formula and counts>],
<candidate gene|comprehensive>; <included|excluded: <reason> (SOP v11 p.<n>)|omitted: lower-quality
candidate evidence (SOP v11 p.35)>"`

Example: `"Fam 2 (PMID 123): AD, eLOD 0.90 from 3 segregations, comprehensive; excluded: AD/XL
eLOD needs >= 4 segregations (SOP v11 p.28)"`.

### 7.3 Trace entry (appended to `rules_applied`)

```json
{"path": "segregation", "rule": "segregation_sop11",
 "families": [{"index": 0, "lod": 1.204, "lod_source": "estimated", "method": "comprehensive",
               "status": "included|excluded|omitted_lower", "rationale": "..."}],
 "sum_candidate": 1.5, "sum_comprehensive": 2.8, "total": 4.3,
 "band": "3-4.99", "C": 1, "D": 2,
 "formula_points": 1.7, "comprehensive_only_points": 2, "points": 2, "max": 3}
```

Preview and save use the same engine call, so the app_user save/preview parity required by #447
holds by construction. Tests: S1, S4-S8 and T1-T5 as engine unit tests, plus one endpoint test
that saves and previews the same payload.

## 8. Orchestrator decisions on the OPEN items (2026-10-31, binding for W11F)

Conservative defaults; each is documented in POINT-MODEL.md and visible in the per-family rationale.

1. OPEN-1: the minimum family size applies to estimated LOD only; a published LOD stands as entered. A published LOD
   covering several families is one row with a note.
2. OPEN-2: the eLOD preconditions (rare, highly penetrant, phenocopies rare) are curator-asserted once per curation;
   if not asserted, every eLOD row is excluded with that reason. No penetrance check by the engine.
3. OPEN-3: consanguinity is not modelled; such pedigrees use a curator-entered adjusted LOD.
4. OPEN-4: the engine does not judge genotype-positive unaffected relatives; the curator enters counts and marks
   unexplained non-segregation, which excludes the family.
5. OPEN-5: exact LOD per family (no rounding), exact sum, displayed to 2 decimals.
6. OPEN-6: daughters of an affected father (0 LOD) do not count toward the 4-segregation minimum.
7. OPEN-7: other inheritance modes accept a curator-entered adjusted LOD only.
8. OPEN-8: gene panels and partial-interval sequencing count as candidate gene.
9. OPEN-9: half-open bands [0,2), [2,3), [3,5), [5,inf) on the exact sum.
10. OPEN-10: round half up to 0.1 (T3 = 0.8).
11. OPEN-11: the curator may override the computed points with a required rationale; an override raises a reviewer flag.
12. OPEN-12: final points = max(formula over all scored families, comprehensive-only); no subset search beyond that.
