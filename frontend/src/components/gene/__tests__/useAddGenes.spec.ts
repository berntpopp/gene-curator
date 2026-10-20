import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { genesAPI, assignmentsAPI } from '@/api'
import { useAddGenes, type BulkValidationResult, type HgncGene } from '../useAddGenes'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/api', () => ({
  genesAPI: { createGene: vi.fn(), bulkCreateGenes: vi.fn() },
  assignmentsAPI: { createAssignment: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const createGene = vi.mocked(genesAPI.createGene)
const bulkCreateGenes = vi.mocked(genesAPI.bulkCreateGenes)
const createAssignment = vi.mocked(assignmentsAPI.createAssignment)
const bulkAssignGenes = vi.mocked(assignmentsAPI.bulkAssignGenes)

const brca1 = {
  hgnc_id: 'HGNC:1100',
  symbol: 'BRCA1',
  name: 'BRCA1 DNA repair associated',
  chromosome: '17',
  location: '17q21.31',
  alias_symbols: ['RNF53'],
  previous_symbols: []
} as unknown as HgncGene

function setup(scopeId: string | null = 'scope-1') {
  const selectedGene = ref<HgncGene | null>(null)
  const bulkValidationResults = ref<BulkValidationResult[]>([])
  const skipDuplicates = ref(true)
  const api = useAddGenes({
    scopeId: () => scopeId,
    selectedGene,
    bulkValidationResults,
    skipDuplicates
  })
  return { api, selectedGene, bulkValidationResults, skipDuplicates }
}

describe('useAddGenes', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  describe('addSingleGene', () => {
    it('does nothing when no gene is selected', async () => {
      const { api } = setup()
      await api.addSingleGene()
      expect(createGene).not.toHaveBeenCalled()
    })

    it('creates the gene and assigns it to the scope as unassigned', async () => {
      createGene.mockResolvedValue({
        id: 'g-1',
        hgnc_id: 'HGNC:1100',
        approved_symbol: 'BRCA1'
      } as never)
      createAssignment.mockResolvedValue({} as never)
      const { api, selectedGene } = setup('scope-1')
      selectedGene.value = brca1

      await api.addSingleGene()

      expect(createGene).toHaveBeenCalledWith({
        hgnc_id: 'HGNC:1100',
        approved_symbol: 'BRCA1',
        chromosome: '17',
        location: '17q21.31',
        previous_symbols: [],
        alias_symbols: ['RNF53'],
        details: { approved_name: 'BRCA1 DNA repair associated' }
      })
      expect(createAssignment).toHaveBeenCalledWith({
        gene_id: 'g-1',
        scope_id: 'scope-1',
        assigned_curator_id: null,
        priority_level: 'medium'
      })
      expect(addToast).toHaveBeenCalledWith('Gene BRCA1 added and assigned to scope', 'success')
    })

    it('reports success without assigning when there is no scope', async () => {
      createGene.mockResolvedValue({
        id: 'g-1',
        hgnc_id: 'HGNC:1100',
        approved_symbol: 'BRCA1'
      } as never)
      const { api, selectedGene } = setup(null)
      selectedGene.value = { hgnc_id: 'HGNC:1', symbol: 'X' } as unknown as HgncGene

      await api.addSingleGene()

      expect(createAssignment).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('Gene BRCA1 added successfully', 'success')
    })

    it('warns when the gene is created but the scope assignment fails', async () => {
      createGene.mockResolvedValue({
        id: 'g-1',
        hgnc_id: 'HGNC:1100',
        approved_symbol: 'BRCA1'
      } as never)
      createAssignment.mockRejectedValue({
        message: 'conflict',
        response: { data: { detail: 'Already assigned' } }
      })
      const { api, selectedGene } = setup()
      selectedGene.value = brca1

      await api.addSingleGene()

      expect(logger.warn).toHaveBeenCalledWith(
        'Gene added but scope assignment failed',
        expect.objectContaining({ gene_id: 'g-1', error: 'conflict' })
      )
      expect(addToast).toHaveBeenCalledWith(
        'Gene BRCA1 added (assignment failed: Already assigned)',
        'warning'
      )
    })

    it('falls back to the error message when the assignment error has no detail', async () => {
      createGene.mockResolvedValue({
        id: 'g-1',
        hgnc_id: 'HGNC:1100',
        approved_symbol: 'BRCA1'
      } as never)
      createAssignment.mockRejectedValue(new Error('network down'))
      const { api, selectedGene } = setup()
      selectedGene.value = brca1

      await api.addSingleGene()

      expect(addToast).toHaveBeenCalledWith(
        'Gene BRCA1 added (assignment failed: network down)',
        'warning'
      )
    })
  })

  describe('addBulkGenes', () => {
    const validRow = { status: 'valid', gene: brca1 } as BulkValidationResult

    it('warns and makes no calls when nothing is valid', async () => {
      const { api, bulkValidationResults } = setup()
      bulkValidationResults.value = [{ status: 'not_found', gene: null }]

      await api.addBulkGenes()

      expect(bulkCreateGenes).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('No valid genes to add', 'warning')
    })

    it('creates valid genes and assigns the created ones to the scope', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 0,
        total_errors: 0,
        created_genes: [{ id: 'g-1' }]
      } as never)
      bulkAssignGenes.mockResolvedValue({} as never)
      const { api, bulkValidationResults, skipDuplicates } = setup('scope-1')
      bulkValidationResults.value = [validRow, { status: 'suggestion', gene: brca1 }]
      skipDuplicates.value = false

      await api.addBulkGenes()

      expect(bulkCreateGenes).toHaveBeenCalledWith({
        genes: [
          {
            hgnc_id: 'HGNC:1100',
            approved_symbol: 'BRCA1',
            chromosome: '17',
            location: '17q21.31',
            details: { approved_name: 'BRCA1 DNA repair associated' }
          }
        ],
        skip_duplicates: false
      })
      expect(bulkAssignGenes).toHaveBeenCalledWith({
        gene_ids: ['g-1'],
        scope_id: 'scope-1',
        assigned_curator_id: null
      })
      expect(addToast).toHaveBeenCalledWith(
        'Added and assigned 1 genes (0 skipped, 0 failed)',
        'success'
      )
    })

    it('uses a warning toast when some genes failed', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 1,
        total_errors: 2,
        created_genes: []
      } as never)
      const { api, bulkValidationResults } = setup(null)
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(bulkAssignGenes).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('Added 1 genes (1 skipped, 2 failed)', 'warning')
    })

    it('does not assign when created_genes is missing', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 0,
        total_skipped: 0,
        total_errors: 0
      } as never)
      const { api, bulkValidationResults } = setup('scope-1')
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(bulkAssignGenes).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('Added 0 genes (0 skipped, 0 failed)', 'success')
    })

    it('warns when the bulk assignment fails after creation', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 0,
        total_errors: 0,
        created_genes: [{ id: 'g-1' }]
      } as never)
      bulkAssignGenes.mockRejectedValue({
        message: 'fail',
        response: { data: { detail: 'Scope closed' } }
      })
      const { api, bulkValidationResults } = setup('scope-1')
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(addToast).toHaveBeenCalledWith(
        'Added 1 genes but scope assignment failed: Scope closed',
        'warning'
      )
    })
  })
})
