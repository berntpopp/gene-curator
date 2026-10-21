// Read the backend-stored computed_scores (scored with the curation's pinned point model).
// No client-side recalculation: caps differ per pinned version (#266).

interface TraceType {
  path: string
  score: number
}
interface TraceCategory {
  key: string
  score: number
  types?: TraceType[]
}
export interface TraceSection {
  key: string
  score: number
  cap?: number | null
  categories?: TraceCategory[]
}

/** Shape of curation.computed_scores as persisted by the scoring engine. */
export interface StoredScores {
  total_score?: number | null
  genetic_evidence_total?: number | null
  experimental_evidence_total?: number | null
  trace?: { sections?: TraceSection[] } | null
}

export interface EvidenceScores {
  caseLevel: { adxlNull: number; adxlOther: number; arNull: number; arOther: number }
  /** Category scores after their caps */
  caseLevelTotal: number
  functionTotal: number
  segregation: number
  caseControl: number
  genetic: number
  function: { biochemical: number; proteinInteraction: number; expression: number }
  functionalAlteration: number
  models: number
  rescue: number
  experimental: number
  total: number
  /** Section caps of the pinned point model; null when uncapped or unknown (legacy rows). */
  caps: { genetic: number | null; experimental: number | null }
  /** False for legacy rows without a stored trace: the breakdown is unknown, not zero. */
  traced: boolean
}

const num = (v: unknown): number => Number(v) || 0

/**
 * Points per kind of evidence (e.g. models, rescue). A kind is its own category, or part of a
 * category several kinds share (SOP v11 "Models & Rescue", capped at 4): then the kinds split
 * the capped score in the given order, so their sum never exceeds the cap.
 */
export function traceKinds(sections: TraceSection[], section: string, kinds: string[]): number[] {
  const categories = sections.find(s => s.key === section)?.categories ?? []
  const left = new Map<TraceCategory, number>()
  return kinds.map(kind => {
    const own = categories.find(c => c.key === kind)
    if (own) return num(own.score)
    const shared = categories.find(c => c.types?.some(t => t.path.startsWith(`${kind}.`)))
    if (!shared) return 0
    const raw = shared.types!.filter(t => t.path.startsWith(`${kind}.`))
    const points = Math.min(
      raw.reduce((sum, t) => sum + num(t.score), 0),
      left.get(shared) ?? num(shared.score)
    )
    left.set(shared, (left.get(shared) ?? num(shared.score)) - points)
    return points
  })
}

/** Map stored computed_scores (totals + trace) onto the display shape; missing parts read 0. */
export function storedScores(stored: StoredScores | null | undefined): EvidenceScores {
  const sections = stored?.trace?.sections ?? []
  const cat = (section: string, key: string) =>
    sections.find(s => s.key === section)?.categories?.find(c => c.key === key)
  const category = (section: string, key: string) => num(cat(section, key)?.score)
  const type = (section: string, key: string, path: string) =>
    num(cat(section, key)?.types?.find(t => t.path === `${key}.${path}`)?.score)
  const cap = (section: string) => sections.find(s => s.key === section)?.cap ?? null
  const caseLevel = (path: string) => type('genetic_evidence', 'case_level', path)
  const [models = 0, rescue = 0] = traceKinds(sections, 'experimental_evidence', [
    'models',
    'rescue'
  ])
  const func = (path: string) => type('experimental_evidence', 'function', path)

  return {
    caseLevel: {
      adxlNull: caseLevel('autosomal_dominant_or_x_linked.predicted_or_proven_null'),
      adxlOther: caseLevel('autosomal_dominant_or_x_linked.other_variant_type'),
      arNull: caseLevel('autosomal_recessive.predicted_or_proven_null'),
      arOther: caseLevel('autosomal_recessive.other_variant_type')
    },
    caseLevelTotal: category('genetic_evidence', 'case_level'),
    functionTotal: category('experimental_evidence', 'function'),
    segregation: category('genetic_evidence', 'segregation'),
    caseControl: category('genetic_evidence', 'case_control'),
    genetic: num(stored?.genetic_evidence_total),
    function: {
      biochemical: func('biochemical_function'),
      proteinInteraction: func('protein_interaction'),
      expression: func('expression')
    },
    functionalAlteration: category('experimental_evidence', 'functional_alteration'),
    models,
    rescue,
    experimental: num(stored?.experimental_evidence_total),
    total: num(stored?.total_score),
    caps: { genetic: cap('genetic_evidence'), experimental: cap('experimental_evidence') },
    traced: sections.length > 0
  }
}
