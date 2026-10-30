import type { RouteLocationRaw } from 'vue-router'
import { formatInheritance } from '@/utils/inheritance'

type Entity = { disease_name?: string | null; mondo_id?: string | null }
type Moi = { mode_of_inheritance?: string | null }

/** "Disease · MONDO id · inheritance · extra" for an entity chooser row. */
export const label = (c: Entity & Moi, ...more: string[]) =>
  [c.disease_name || 'Disease not set', c.mondo_id]
    .concat(c.mode_of_inheritance ? formatInheritance(c.mode_of_inheritance) : [], more)
    .filter(Boolean)
    .join(' · ')

/** One row per approved entity (#530): its open curation opens, its active one is re-curated
 * (the ?from prefill flow), otherwise a new curation starts for it. Legacy open curations
 * without an entity link get their own row so they can be continued. */
export function entityChoices(
  entities: (Entity & Moi & { id: string })[],
  curations: (Entity & Moi & { id: string; status: string; precuration_id?: string | null })[], // not archived
  scopeId: string
): { id: string; label: string; to: RouteLocationRaw }[] {
  const edit = (id: string) => ({ name: 'curation-edit', params: { scopeId, curationId: id } })
  const legacy = curations
    .filter(c => !c.precuration_id && c.status !== 'active')
    .map(c => ({ id: c.id, label: label(c, c.status), to: edit(c.id) }))
  return entities
    .map(p => {
      const mine = curations.filter(c => c.precuration_id === p.id)
      const open = mine.find(c => c.status !== 'active')
      const active = mine.find(c => c.status === 'active')
      const to = open
        ? edit(open.id)
        : { query: active ? { from: active.id } : { precuration_id: p.id } }
      return { id: p.id, label: label(p, (open ?? active)?.status ?? 'not started'), to }
    })
    .concat(legacy)
}
