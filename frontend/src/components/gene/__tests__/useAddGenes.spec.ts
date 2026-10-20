import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { genesAPI, assignmentsAPI } from '@/api'
import { useAddGenes, type BulkValidationResult, type HgncGene } from '../useAddGenes'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const addToast = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/api', () => ({
  genesAPI: { createGene: vi.fn(), bulkCreateGenes: vi.fn(), searchGenes: vi.fn() },
  assignmentsAPI: { createAssignment: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const createGene = vi.mocked(genesAPI.createGene)
const searchGenes = vi.mocked(genesAPI.searchGenes)
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
    searchGenes.mockResolvedValue([])
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

    it('assigns a gene that already exists in the catalogue without creating it', async () => {
      searchGenes.mockResolvedValue([
        { id: 'g-pkd1', hgnc_id: 'HGNC:9008', approved_symbol: 'PKD1' }
      ] as never)
      createAssignment.mockResolvedValue({} as never)
      const { api, selectedGene } = setup('scope-1')
      selectedGene.value = brca1

      await api.addSingleGene()

      expect(searchGenes).toHaveBeenCalledWith({ hgnc_id: 'HGNC:1100' })
      expect(createGene).not.toHaveBeenCalled()
      expect(createAssignment).toHaveBeenCalledWith(
        expect.objectContaining({ gene_id: 'g-pkd1', scope_id: 'scope-1' })
      )
      expect(addToast).toHaveBeenCalledWith('Gene PKD1 added and assigned to scope', 'success')
    })

    it('says so when the gene is already in this scope', async () => {
      searchGenes.mockResolvedValue([{ id: 'g-1', approved_symbol: 'PKD1' }] as never)
      createAssignment.mockRejectedValue({
        message: 'bad request',
        response: { data: { detail: 'Gene is already assigned to this scope' } }
      })
      const { api, selectedGene } = setup('scope-1')
      selectedGene.value = brca1

      await api.addSingleGene()

      expect(addToast).toHaveBeenCalledWith('Gene PKD1 is already in this scope', 'info')
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
    const validRow: BulkValidationResult = {
      input: 'BRCA1',
      status: 'valid',
      gene: brca1,
      alternatives: []
    }

    it('warns and makes no calls when nothing is valid', async () => {
      const { api, bulkValidationResults } = setup()
      bulkValidationResults.value = [
        { input: 'X', status: 'not_found', gene: null, alternatives: [] }
      ]

      await api.addBulkGenes()

      expect(bulkCreateGenes).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('No valid genes to add', 'warning')
    })

    it('creates valid genes and assigns the created ones to the scope', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 0,
        total_errors: 0,
        created_genes: [{ id: 'g-1' }],
        skipped_genes: []
      } as never)
      bulkAssignGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 0,
        total_errors: 0
      } as never)
      const { api, bulkValidationResults, skipDuplicates } = setup('scope-1')
      bulkValidationResults.value = [validRow, { ...validRow, status: 'suggestion' }]
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
        validate_hgnc: true,
        skip_duplicates: false
      })
      expect(bulkAssignGenes).toHaveBeenCalledWith({
        gene_ids: ['g-1'],
        scope_id: 'scope-1',
        assigned_curator_id: null,
        priority_level: 'medium'
      })
      expect(addToast).toHaveBeenCalledWith(
        'Added 1 genes to the scope (0 already in scope, 0 failed)',
        'success'
      )
    })

    it('assigns catalogue genes skipped as duplicates together with the created ones', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 1,
        total_errors: 0,
        created_genes: [{ id: 'g-1' }],
        skipped_genes: [{ hgnc_id: 'HGNC:9008' }]
      } as never)
      searchGenes.mockResolvedValue([{ id: 'g-pkd1' }] as never)
      bulkAssignGenes.mockResolvedValue({
        total_created: 2,
        total_skipped: 0,
        total_errors: 0
      } as never)
      const { api, bulkValidationResults } = setup('scope-1')
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(searchGenes).toHaveBeenCalledWith({ hgnc_id: 'HGNC:9008' })
      expect(bulkAssignGenes).toHaveBeenCalledWith(
        expect.objectContaining({ gene_ids: ['g-1', 'g-pkd1'], scope_id: 'scope-1' })
      )
    })

    it('reports genes that are already in the scope', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 0,
        total_skipped: 1,
        total_errors: 0,
        created_genes: [],
        skipped_genes: [{ hgnc_id: 'HGNC:9008' }]
      } as never)
      searchGenes.mockResolvedValue([{ id: 'g-pkd1' }] as never)
      bulkAssignGenes.mockResolvedValue({
        total_created: 0,
        total_skipped: 1,
        total_errors: 0
      } as never)
      const { api, bulkValidationResults } = setup('scope-1')
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(addToast).toHaveBeenCalledWith(
        'Added 0 genes to the scope (1 already in scope, 0 failed)',
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

    it('does not assign when there are no genes to assign', async () => {
      bulkCreateGenes.mockResolvedValue({
        created_genes: [],
        skipped_genes: [],
        total_created: 0,
        total_skipped: 0,
        total_errors: 0
      } as never)
      const { api, bulkValidationResults } = setup('scope-1')
      bulkValidationResults.value = [validRow]

      await api.addBulkGenes()

      expect(bulkAssignGenes).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith(
        'Added 0 genes to the scope (0 already in scope, 0 failed)',
        'success'
      )
    })

    it('warns when the bulk assignment fails after creation', async () => {
      bulkCreateGenes.mockResolvedValue({
        total_created: 1,
        total_skipped: 0,
        total_errors: 0,
        created_genes: [{ id: 'g-1' }],
        skipped_genes: []
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
