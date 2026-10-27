import { describe, it, expect, vi, beforeEach } from 'vitest'
import { precurationsAPI, curationsAPI } from '@/api'
import {
  shouldReplaceCuration,
  shouldReplacePrecuration,
  useGeneWorkflowStatus,
  type CurationStatus,
  type PrecurationStatus
} from '../useGeneWorkflowStatus'

const logger = vi.hoisted(() => ({
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => logger
}))

vi.mock('@/api', () => ({
  precurationsAPI: { getPrecurations: vi.fn() },
  curationsAPI: { getCurations: vi.fn() }
}))

const getPrecurations = vi.mocked(precurationsAPI.getPrecurations)
const getCurations = vi.mocked(curationsAPI.getCurations)

function precuration(status: string, updated_at: string): PrecurationStatus {
  return { id: `p-${status}`, status, updated_at }
}

function curation(status: string, updated_at: string): CurationStatus {
  return { id: `c-${status}`, status, updated_at }
}

describe('shouldReplacePrecuration', () => {
  it('prefers a higher-ranked status', () => {
    expect(
      shouldReplacePrecuration(
        precuration('draft', '2025-01-01'),
        precuration('approved', '2024-01-01')
      )
    ).toBe(true)
    expect(
      shouldReplacePrecuration(
        precuration('approved', '2025-01-01'),
        precuration('draft', '2026-01-01')
      )
    ).toBe(false)
  })

  it('uses the newer record when the status ties', () => {
    expect(
      shouldReplacePrecuration(
        precuration('draft', '2025-01-01'),
        precuration('draft', '2025-02-01')
      )
    ).toBe(true)
    expect(
      shouldReplacePrecuration(
        precuration('draft', '2025-02-01'),
        precuration('draft', '2025-01-01')
      )
    ).toBe(false)
  })

  it('ranks unknown statuses lowest', () => {
    expect(
      shouldReplacePrecuration(
        precuration('weird', '2025-01-01'),
        precuration('rejected', '2024-01-01')
      )
    ).toBe(false)
  })
})

describe('shouldReplaceCuration', () => {
  it('ranks a curation in review like a submitted one (#403)', () => {
    expect(
      shouldReplaceCuration(curation('rejected', '2026-01-01'), curation('in_review', '2025-01-01'))
    ).toBe(true)
    expect(
      shouldReplaceCuration(curation('in_review', '2025-01-01'), curation('draft', '2026-01-01'))
    ).toBe(false)
  })

  it('ranks active above approved and archived lowest', () => {
    expect(
      shouldReplaceCuration(curation('approved', '2025-01-01'), curation('active', '2024-01-01'))
    ).toBe(true)
    expect(
      shouldReplaceCuration(curation('active', '2025-01-01'), curation('archived', '2026-01-01'))
    ).toBe(false)
  })

  it('uses the newer record when the status ties', () => {
    expect(
      shouldReplaceCuration(
        curation('submitted', '2025-01-01'),
        curation('submitted', '2025-03-01')
      )
    ).toBe(true)
  })
})

describe('useGeneWorkflowStatus', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('keeps the highest-ranked precuration per gene', async () => {
    getPrecurations.mockResolvedValue({
      precurations: [
        { id: 'p1', gene_id: 'g1', status: 'draft', updated_at: '2025-01-01' },
        { id: 'p2', gene_id: 'g1', status: 'approved', updated_at: '2024-06-01' },
        {
          id: 'p3',
          gene_id: 'g2',
          status: 'submitted',
          updated_at: '2025-02-01',
          workflow_stage: 'review'
        }
      ]
    } as never)

    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchPrecurationStatuses()

    expect(getPrecurations).toHaveBeenCalledWith({ scope_id: 'scope-1', skip: 0, limit: 200 })
    expect(workflow.genePrecurations.value.g1).toMatchObject({ id: 'p2', status: 'approved' })
    expect(workflow.genePrecurations.value.g2).toMatchObject({ id: 'p3', workflow_stage: 'review' })
    expect(workflow.hasPrecuration({ gene_id: 'g1' })).toBe(true)
    expect(workflow.isPrecurationApproved({ gene_id: 'g1' })).toBe(true)
    expect(workflow.isPrecurationApproved({ gene_id: 'g2' })).toBe(false)
    expect(workflow.getPrecurationStatusLabel({ gene_id: 'g2' })).toBe('Pending Review')
    expect(workflow.getPrecurationStatusLabel({ gene_id: 'g3' })).toBe('No Precuration')
  })

  it('labels unknown precuration statuses with the raw status', async () => {
    getPrecurations.mockResolvedValue({
      precurations: [{ id: 'p1', gene_id: 'g1', status: 'odd', updated_at: '2025-01-01' }]
    } as never)
    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchPrecurationStatuses()
    expect(workflow.getPrecurationStatusLabel({ gene_id: 'g1' })).toBe('odd')
  })

  it('logs and keeps the previous map when the precuration request fails', async () => {
    getPrecurations.mockRejectedValue(new Error('boom'))
    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchPrecurationStatuses()
    expect(logger.error).toHaveBeenCalledWith('Failed to fetch precuration statuses', {
      error: 'boom'
    })
    expect(workflow.genePrecurations.value).toEqual({})
  })

  it('keeps the most relevant curation per gene and reports curation predicates', async () => {
    getCurations.mockResolvedValue({
      curations: [
        { id: 'c1', gene_id: 'g1', status: 'draft', updated_at: '2025-01-01' },
        { id: 'c2', gene_id: 'g1', status: 'active', updated_at: '2024-01-01' },
        { id: 'c3', gene_id: 'g2', status: 'draft', updated_at: '2025-01-01' }
      ]
    } as never)

    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchCurationStatuses()

    expect(getCurations).toHaveBeenCalledWith({ scope_id: 'scope-1', skip: 0, limit: 200 })
    expect(workflow.hasCuration({ gene_id: 'g1' })).toBe(true)
    expect(workflow.hasCuration({ gene_id: 'g9' })).toBe(false)
    expect(workflow.isCurationActive({ gene_id: 'g1' })).toBe(true)
    expect(workflow.isCurationActive({ gene_id: 'g2' })).toBe(false)
    expect(workflow.getCuration({ gene_id: 'g2' })).toMatchObject({ id: 'c3' })
    expect(workflow.getCurationStatusLabel({ gene_id: 'g2' })).toBe('Draft')
    expect(workflow.getCurationStatusLabel({ gene_id: 'g9' })).toBe('No Curation')
  })

  it('pages through more than 200 curations and precurations', async () => {
    const rows = (from: number, n: number, prefix: string) =>
      Array.from({ length: n }, (_, i) => ({
        id: `${prefix}${from + i}`,
        gene_id: `g${from + i}`,
        status: 'draft',
        updated_at: '2025-01-01'
      }))
    getCurations
      .mockResolvedValueOnce({ curations: rows(0, 200, 'c'), total: 250 } as never)
      .mockResolvedValueOnce({ curations: rows(200, 50, 'c'), total: 250 } as never)
    getPrecurations
      .mockResolvedValueOnce({ precurations: rows(0, 200, 'p'), total: 250 } as never)
      .mockResolvedValueOnce({ precurations: rows(200, 50, 'p'), total: 250 } as never)

    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchCurationStatuses()
    await workflow.fetchPrecurationStatuses()

    expect(getCurations).toHaveBeenLastCalledWith({ scope_id: 'scope-1', skip: 200, limit: 200 })
    expect(getPrecurations).toHaveBeenLastCalledWith({ scope_id: 'scope-1', skip: 200, limit: 200 })
    expect(workflow.hasCuration({ gene_id: 'g249' })).toBe(true)
    expect(workflow.hasPrecuration({ gene_id: 'g249' })).toBe(true)
  })

  it('labels unknown curation statuses with the raw status', async () => {
    getCurations.mockResolvedValue({
      curations: [{ id: 'c1', gene_id: 'g1', status: 'odd', updated_at: '2025-01-01' }]
    } as never)
    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchCurationStatuses()
    expect(workflow.getCurationStatusLabel({ gene_id: 'g1' })).toBe('odd')
  })

  it('logs and keeps the previous map when the curation request fails', async () => {
    getCurations.mockRejectedValue(new Error('down'))
    const workflow = useGeneWorkflowStatus(() => 'scope-1')
    await workflow.fetchCurationStatuses()
    expect(logger.error).toHaveBeenCalledWith('Failed to fetch curation statuses', {
      error: 'down'
    })
    expect(workflow.geneCurations.value).toEqual({})
  })
})
