import { curationsAPI } from '@/api'

type Entity = {
  id?: string
  gene_id?: string
  scope_id?: string
  precuration_id?: string | null
  mondo_id?: string | null
  mode_of_inheritance?: string | null
  relationship_type?: string | null
}

/** Whether approving `c` replaces an active curation of its own disease entity (#530): the
 * same precuration, or the same MONDO id, inheritance and relationship type. */
export async function replacesActive(c: Entity): Promise<boolean> {
  const { curations } = await curationsAPI.getCurations({
    scope_id: c.scope_id,
    gene_id: c.gene_id,
    curation_status: 'active'
  })
  for (const row of curations.filter(r => r.id !== c.id)) {
    const a = await curationsAPI.getCuration(row.id)
    const same =
      (!!c.precuration_id && a.precuration_id === c.precuration_id) ||
      (a.mondo_id === c.mondo_id &&
        a.mode_of_inheritance === c.mode_of_inheritance &&
        (a.relationship_type ?? 'mendelian') === (c.relationship_type ?? 'mendelian'))
    if (same) return true
  }
  return false
}
