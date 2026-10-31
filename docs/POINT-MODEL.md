# Point model

A curation schema scores evidence with `scoring_configuration.point_model`, interpreted by
`backend/app/scoring/point_model.py`. A methodology that is not ClinGen SOP v11 declares
`"engine": "point_model"` (same interpreter, neutral name; it must carry its own `point_model`).
`"engine": "clingen_sop_v11"` falls back to the bundled ClinGen template when no model is given.

```json
{
  "total_cap": 18,
  "sections": [{"key": "genetic_evidence", "cap": 12, "categories": [
    {"key": "probands", "cap": 10, "types": [{"path": "probands", "default": 1, "range": [0, 3]}]}
  ]}],
  "overrides": [{"when": "contradictory_evidence", "field": "impact", "in": ["disputed"], "class": "disputed"}],
  "bands": [{"class": "strong", "min": 12}, {"class": "limited", "min": 0.1}, {"class": "no_known"}]
}
```

A section `key` is a top-level evidence field; a type `path` is dotted below it and names an
evidence table. Other type keys: `points_key`, `rule` (`case_row`, `explicit_points`,
`segregation`, `step`), `group_by` + `group_cap`, `require_variant`. Bands take `min`,
`requires`, `section_min`; `review_flags` and `classifications` are described in the code.
The `review_flags.hotspot` warning (`max_variants`, `min_share`) means recurrence: the top
`max_variants` variants carry at least `min_share` of the proband points and at least one
of them appears in 2 or more scoring proband rows (counted before a group cap).

## Row rules: `points_when`

A type's `points_when` sets a row's points from the row's own fields:

```json
"points_when": [
  {"field": "de_novo", "in": ["confirmed"], "points": 1.5},
  {"field": "duplicate_of", "present": true, "points": 0},
  {"field": "phase", "in": ["not_given", "unknown"], "points": 0},
  {"field": "allele_frequency", "gt": 0.0025, "points": 0},
  {"field": "allele_frequency", "gt": 0.0001,
   "and": [{"field": "zygosity", "in": ["heterozygous", "hemizygous"]}], "points": 0}
]
```

The AF example needs zygosity values that tell AD/XL rows from AR rows: AR rows carry their own
values (e.g. `homozygous`, `compound_heterozygous`) so only the 2.5e-3 cutoff applies to them.

A condition is `field` plus at least one of `in` (strict: `true` is not `1`), `gt`, `gte`, `lt`,
`lte` (need a number; text such as `"0.01"` is read as one) and `present` (`true`: the value is
set, not missing, null or a blank string; `false`: it is not). `and` adds conditions on other
fields of the same row.

Order of operations per row:

1. The type's rule gives the row's points: the entered points, else the type's `default`
   (blank form rows count nothing and stop here).
2. Every `points_when` rule is checked. A matching rule with `points: 0` (an exclusion) wins,
   wherever it stands in the list.
3. Otherwise the first matching rule fills the points only when the curator left the points
   blank; points the curator entered (0 included) stand.
4. The range check (#278), the citation policy (no PMID scores 0) and `group_cap` apply to the
   result, then category, section and total caps.

## Step rule

`"rule": "step"` sums `field` over the type's rows and scores the highest step reached as one item:

```json
{"path": "segregation", "rule": "step", "field": "lod",
 "steps": [{"min": 2, "points": 1}, {"min": 3, "points": 2}, {"min": 5, "points": 3}]}
```

Rows without a value add nothing, uncited rows with a positive value are listed in `excluded`,
and a value that is not a number is flagged in `out_of_range`. `steps[].min` must increase.

## Trace

Each applied rule is listed in the score trace under `rules_applied`:
`{path, rule: "points_when", index, entered, points, applied}` per row with a matching rule
(`applied: false` means the curator's entered points were kept) and
`{path, rule: "step", field, sum, points}` per step type. Traces without applied rules are unchanged.

## Validation

Creating and publishing a schema rejects a point model whose section keys, type paths,
`points_when`/step fields or override `when`/`field` name no field in `field_definitions`
(a typo would otherwise score 0 silently), and any `visible_when`/`show_when` path that names no
field. Path checks are skipped when no section key is a field at all, and below a section stored
as a flat list (legacy evidence scored without paths).
