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
    expect(r).toEqual({ added: 2, alreadyInScope: 1, failed: 0 })
  })

  it('creates genes that only exist at HGNC, including ones created meanwhile', async () => {
    bulkCreate.mockResolvedValue({
      created_genes: [{ id: 'new1' }],
      skipped_genes: [{ hgnc_id: 'HGNC:3' }, { hgnc_id: 'HGNC:4' }],
      total_errors: 1
    } as never)
    search.mockResolvedValueOnce([{ id: 'old3' }] as never).mockResolvedValueOnce([])
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
    expect(r).toEqual({ added: 2, alreadyInScope: 0, failed: 1 })
  })

  it('does not call the assignment endpoint when nothing could be created', async () => {
    bulkCreate.mockResolvedValue({ created_genes: [], skipped_genes: [], total_errors: 2 } as never)
    const r = await useGeneIntakeStore().addToScope('s1', [
      { hgnc_id: 'HGNC:2', symbol: 'B', gene_id: null }
    ])
    expect(bulkAssign).not.toHaveBeenCalled()
    expect(r).toEqual({ added: 0, alreadyInScope: 0, failed: 2 })
  })
})
