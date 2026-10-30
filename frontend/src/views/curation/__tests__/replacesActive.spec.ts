import { describe, it, expect, vi, beforeEach } from 'vitest'
import { curationsAPI } from '@/api'
import { replacesActive } from '../replacesActive'

vi.mock('@/api', () => ({ curationsAPI: { getCurations: vi.fn(), getCuration: vi.fn() } }))

const entity = { mondo_id: 'MONDO:1', mode_of_inheritance: 'AD', relationship_type: 'mendelian' }
const me = { id: 'new', gene_id: 'g', scope_id: 's', precuration_id: 'p-new', ...entity }

describe('replacesActive', () => {
  beforeEach(() => {
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({
      curations: [{ id: 'new' }, { id: 'act' }]
    } as never)
  })

  it('is true for an active curation of the same entity, never for itself', async () => {
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({ id: 'act', ...entity } as never)
    expect(await replacesActive(me)).toBe(true)
    expect(curationsAPI.getCurations).toHaveBeenCalledWith({
      scope_id: 's',
      gene_id: 'g',
      curation_status: 'active'
    })
    expect(curationsAPI.getCuration).toHaveBeenCalledTimes(1)
  })

  it('is false for another entity of the gene (susceptibility) or no active curation', async () => {
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({
      id: 'act',
      ...entity,
      relationship_type: 'susceptibility'
    } as never)
    expect(await replacesActive(me)).toBe(false)
    vi.mocked(curationsAPI.getCurations).mockResolvedValue({ curations: [] } as never)
    expect(await replacesActive(me)).toBe(false)
  })

  it('is true for an active curation of the same precuration', async () => {
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({
      id: 'act',
      precuration_id: 'p-new'
    } as never)
    expect(await replacesActive(me)).toBe(true)
  })
})
