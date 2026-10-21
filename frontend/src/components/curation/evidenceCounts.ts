type Rows = Record<string, unknown> | unknown[] | null | undefined

export function rows(node: unknown): Record<string, unknown>[] {
  if (Array.isArray(node)) return node as Record<string, unknown>[]
  if (node && typeof node === 'object') return Object.values(node).flatMap(rows)
  return []
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** One-line summary for the reviewer: rows per category and distinct PMIDs. */
export function evidenceCountsText(
  evidence: { [category: string]: unknown } | null | undefined
): string {
  const groups = [
    ['Genetic', rows(evidence?.genetic_evidence as Rows)],
    ['Experimental', rows(evidence?.experimental_evidence as Rows)],
    ['Contradictory', rows(evidence?.contradictory_evidence as Rows)]
  ] as const
  const pmids = new Set(groups.flatMap(([, r]) => r.map(i => i.pmid).filter(Boolean)))
  return [
    ...groups.map(([name, r]) => `${name}: ${plural(r.length, 'item')}`),
    plural(pmids.size, 'PMID')
  ].join(' · ')
}
