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
interface TraceSection {
  key: string
  score: number
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
  segregation: number
  caseControl: number
  genetic: number
  function: { biochemical: number; proteinInteraction: number; expression: number }
  functionalAlteration: number
  models: number
  rescue: number
  experimental: number
  total: number
}

const num = (v: unknown): number => Number(v) || 0

/** Map stored computed_scores (totals + trace) onto the display shape; missing parts read 0. */
export function storedScores(stored: StoredScores | null | undefined): EvidenceScores {
  const sections = stored?.trace?.sections ?? []
  const cat = (section: string, key: string) =>
    sections.find(s => s.key === section)?.categories?.find(c => c.key === key)
  const category = (section: string, key: string) => num(cat(section, key)?.score)
  const type = (section: string, key: string, path: string) =>
    num(cat(section, key)?.types?.find(t => t.path === `${key}.${path}`)?.score)
  const caseLevel = (path: string) => type('genetic_evidence', 'case_level', path)
  const func = (path: string) => type('experimental_evidence', 'function', path)

  return {
    caseLevel: {
      adxlNull: caseLevel('autosomal_dominant_or_x_linked.predicted_or_proven_null'),
      adxlOther: caseLevel('autosomal_dominant_or_x_linked.other_variant_type'),
      arNull: caseLevel('autosomal_recessive.predicted_or_proven_null'),
      arOther: caseLevel('autosomal_recessive.other_variant_type')
    },
    segregation: category('genetic_evidence', 'segregation'),
    caseControl: category('genetic_evidence', 'case_control'),
    genetic: num(stored?.genetic_evidence_total),
    function: {
      biochemical: func('biochemical_function'),
      proteinInteraction: func('protein_interaction'),
      expression: func('expression')
    },
    functionalAlteration: category('experimental_evidence', 'functional_alteration'),
    models: category('experimental_evidence', 'models'),
    rescue: category('experimental_evidence', 'rescue'),
    experimental: num(stored?.experimental_evidence_total),
    total: num(stored?.total_score)
  }
}
