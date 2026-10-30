import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGeneIntakeStore } from '@/stores/geneIntake'
import { geneResolveAPI } from '@/api/geneResolve'
import { genesAPI } from '@/api/genes'
import { assignmentsAPI } from '@/api/assignments'

vi.mock('@/api/geneResolve', () => ({ geneResolveAPI: { resolve: vi.fn() } }))
vi.mock('@/api/genes', () => ({ genesAPI: { bulkCreateGenes: vi.fn(), searchGenes: vi.fn() } }))
vi.mock('@/api/assignments', () => ({ assignmentsAPI: { bulkAssignGenes: vi.fn() } }))

const bulkCreate = vi.mocked(genesAPI.bulkCreateGenes)
const search = vi.mocked(genesAPI.searchGenes)
const bulkAssign = vi.mocked(assignmentsAPI.bulkAssignGenes)
const assigned = { total_created: 2, total_skipped: 1, total_errors: 0 } as never

describe('geneIntake store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    ;[bulkCreate, search, bulkAssign].forEach(m => m.mockReset())
  })

  it('resolves through the API', async () => {
    vi.mocked(geneResolveAPI.resolve).mockResolvedValue({ items: [], counts: {} } as never)
    await useGeneIntakeStore().resolve(['PKD1'])
    expect(geneResolveAPI.resolve).toHaveBeenCalledWith(['PKD1'])
  })

  it('assigns local genes directly in one bulk request', async () => {
    bulkAssign.mockResolvedValue(assigned)
    const r = await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:1', symbol: 'A', gene_id: 'g1' },
      { hgnc_id: 'HGNC:2', symbol: 'B', gene_id: 'g2' }
    ])
    expect(bulkCreate).not.toHaveBeenCalled()
    expect(bulkAssign).toHaveBeenCalledWith({
      gene_ids: ['g1', 'g2'],
      scope_id: 's1',
      assigned_curator_id: null,
      priority_level: 'medium'
    })
    expect(r).toEqual({ added: 2, alreadyInScope: 1, failed: 0, notAssigned: 0 })
  })

  it('creates genes that only exist at HGNC, including ones created meanwhile', async () => {
    bulkCreate.mockResolvedValue({
      created_genes: [{ id: 'new1' }],
      skipped_genes: [{ hgnc_id: 'HGNC:3' }, { hgnc_id: 'HGNC:4' }],
      total_errors: 1
    } as never)
    search
      .mockResolvedValueOnce([{ id: 'old3', hgnc_id: 'HGNC:3' }] as never)
      .mockResolvedValueOnce([])
    bulkAssign.mockResolvedValue({ total_created: 2, total_skipped: 0, total_errors: 0 } as never)

    const r = await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:1', symbol: 'A', name: 'a gene', gene_id: 'g1' },
      { hgnc_id: 'HGNC:2', symbol: 'B', name: 'b gene', gene_id: null },
      { hgnc_id: 'HGNC:3', symbol: 'C', gene_id: null }
    ])

    expect(bulkCreate.mock.calls[0]![0].genes).toEqual([
      { hgnc_id: 'HGNC:2', approved_symbol: 'B', details: { approved_name: 'b gene' } },
      { hgnc_id: 'HGNC:3', approved_symbol: 'C', details: undefined }
    ])
    expect(bulkAssign.mock.calls[0]![0].gene_ids).toEqual(['g1', 'new1', 'old3'])
    expect(r).toEqual({ added: 2, alreadyInScope: 0, failed: 2, notAssigned: 0 })
  })

  it('does not call the assignment endpoint when nothing could be created', async () => {
    bulkCreate.mockResolvedValue({ created_genes: [], skipped_genes: [], total_errors: 2 } as never)
    const r = await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:2', symbol: 'B', gene_id: null }
    ])
    expect(bulkAssign).not.toHaveBeenCalled()
    expect(r).toEqual({ added: 0, alreadyInScope: 0, failed: 2, notAssigned: 0 })
  })

  it('sends create and assign in chunks of 100, creating before assigning', async () => {
    const order: string[] = []
    bulkCreate.mockImplementation(async ({ genes }) => {
      order.push(`create${genes.length}`)
      return {
        created_genes: genes.map(g => ({ id: `id-${g.hgnc_id}` })),
        skipped_genes: [],
        total_errors: 0
      } as never
    })
    bulkAssign.mockImplementation(async ({ gene_ids }) => {
      order.push(`assign${gene_ids.length}`)
      return { total_created: gene_ids.length, total_skipped: 0, total_errors: 0 } as never
    })
    const picks = Array.from({ length: 250 }, (_, i) => ({
      hgnc_id: `HGNC:${i}`,
      symbol: `G${i}`,
      gene_id: null
    }))
    const r = await useGeneIntakeStore().addToScope('s1', picks)
    expect(order).toEqual([
      'create100',
      'create100',
      'create50',
      'assign100',
      'assign100',
      'assign50'
    ])
    expect(r).toEqual({ added: 250, alreadyInScope: 0, failed: 0, notAssigned: 0 })
  })

  it('counts a failed chunk as failed and carries on with the others', async () => {
    bulkAssign
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce({ total_created: 20, total_skipped: 0, total_errors: 0 } as never)
    const picks = Array.from({ length: 120 }, (_, i) => ({
      hgnc_id: `HGNC:${i}`,
      symbol: `G${i}`,
      gene_id: `g${i}`
    }))
    const r = await useGeneIntakeStore().addToScope('s1', picks)
    expect(r).toEqual({ added: 20, alreadyInScope: 0, failed: 100, notAssigned: 0 })
  })

  it('sends a gene once even when several rows point at it', async () => {
    bulkAssign.mockResolvedValue(assigned)
    await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:1', symbol: 'A', gene_id: 'g1' },
      { hgnc_id: 'HGNC:1', symbol: 'A', gene_id: 'g1' }
    ])
    expect(bulkAssign.mock.calls[0]![0].gene_ids).toEqual(['g1'])
  })

  it('ignores a lookup result for a different HGNC id', async () => {
    bulkCreate.mockResolvedValue({
      created_genes: [],
      skipped_genes: [{ hgnc_id: 'HGNC:3' }],
      total_errors: 0
    } as never)
    search.mockResolvedValue([{ id: 'other', hgnc_id: 'HGNC:99' }] as never)
    const r = await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:3', symbol: 'C', gene_id: null }
    ])
    expect(bulkAssign).not.toHaveBeenCalled()
    expect(r.added).toBe(0)
  })

  it.each([
    ['lookup throws', () => search.mockRejectedValue(new Error('x')), 2],
    [
      'lookup finds only some',
      () =>
        search
          .mockResolvedValueOnce([{ id: 'o3', hgnc_id: 'HGNC:3' }] as never)
          .mockResolvedValue([]),
      1
    ]
  ])('keeps added + alreadyInScope + failed equal to picks when %s', async (_n, setup, failed) => {
    bulkCreate.mockResolvedValue({
      created_genes: [{ id: 'n1' }],
      skipped_genes: [{ hgnc_id: 'HGNC:3' }, { hgnc_id: 'HGNC:4' }],
      total_errors: 0
    } as never)
    setup()
    bulkAssign.mockImplementation(
      async ({ gene_ids }) =>
        ({ total_created: gene_ids.length, total_skipped: 0, total_errors: 0 }) as never
    )
    const picks = [1, 3, 4].map(i => ({ hgnc_id: `HGNC:${i}`, symbol: `G${i}`, gene_id: null }))
    const r = await useGeneIntakeStore().addToScope('s1', picks)
    expect(r.added + r.alreadyInScope + r.failed).toBe(3)
    expect(r.failed).toBe(failed)
  })
})
