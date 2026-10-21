import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AxiosResponse } from 'axios'
import apiClient from '../client'
import { authAPI } from '../auth'
import { scopesAPI } from '../scopes'
import { schemasAPI } from '../schemas'
import { validationAPI } from '../validation'
import { genesAPI } from '../genes'
import { catalogueMatrixAPI } from '../catalogueMatrix'
import { assignmentsAPI } from '../assignments'
import { curationsAPI } from '../curations'
import { precurationsAPI } from '../precurations'
import { externalValidationAPI } from '../externalValidation'
import { ontologyAPI } from '../ontology'
import { workflowAPI } from '../workflow'
import { geneSummaryAPI } from '../geneSummary'
import { invitationsApi } from '../invitations'
import { publicationsAPI } from '../publications'
import * as apiIndex from '../index'
import { identityRows } from './endpointRows'
import { clinicalRows } from './endpointRowsClinical'

vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn()
  }
}))

const PAYLOAD = 'payload'
const client = vi.mocked(apiClient)

function response(data: unknown): AxiosResponse {
  return { data } as AxiosResponse
}

const rows = [...identityRows, ...clinicalRows]

describe('API modules: request shape and response passthrough', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    client.get.mockResolvedValue(response(PAYLOAD))
    client.post.mockResolvedValue(response(PAYLOAD))
    client.put.mockResolvedValue(response(PAYLOAD))
    client.patch.mockResolvedValue(response(PAYLOAD))
    client.delete.mockResolvedValue(response(PAYLOAD))
  })

  it.each(rows)('$name', async row => {
    const value = await row.run()

    expect(client[row.method]).toHaveBeenCalledWith(...row.args)
    expect(value).toBe('result' in row ? row.result : PAYLOAD)
  })

  it('exposes every module through the api index', () => {
    expect(apiIndex.authAPI).toBe(authAPI)
    expect(apiIndex.scopesAPI).toBe(scopesAPI)
    expect(apiIndex.schemasAPI).toBe(schemasAPI)
    expect(apiIndex.validationAPI).toBe(validationAPI)
    expect(apiIndex.workflowAPI).toBe(workflowAPI)
    expect(apiIndex.genesAPI).toBe(genesAPI)
    expect(apiIndex.catalogueMatrixAPI).toBe(catalogueMatrixAPI)
    expect(apiIndex.assignmentsAPI).toBe(assignmentsAPI)
    expect(apiIndex.precurationsAPI).toBe(precurationsAPI)
    expect(apiIndex.curationsAPI).toBe(curationsAPI)
    expect(apiIndex.externalValidationAPI).toBe(externalValidationAPI)
    expect(apiIndex.ontologyAPI).toBe(ontologyAPI)
    expect(apiIndex.publicationsAPI).toBe(publicationsAPI)
    expect(apiIndex.apiClient).toBe(apiClient)
  })
})

describe('API modules: response-specific behaviour', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('countSearchGenes returns the number from /genes/search/count', async () => {
    client.get.mockResolvedValue({ data: 7 })
    await expect(genesAPI.countSearchGenes({ query: 'x' })).resolves.toBe(7)
    expect(client.get).toHaveBeenCalledWith('/genes/search/count', { params: { query: 'x' } })
  })

  it('generateJsonSchema returns the JSONSchemaResponse body', async () => {
    client.get.mockResolvedValue({ data: { json_schema: { type: 'object' } } })
    await expect(validationAPI.generateJsonSchema('s1')).resolves.toEqual({
      json_schema: { type: 'object' }
    })
    expect(client.get).toHaveBeenCalledWith('/validation/schema/s1/json-schema')
  })

  it('getAvailableTransitions returns the list or an empty array', async () => {
    client.get.mockResolvedValueOnce({ data: { available_transitions: ['review'] } })
    await expect(workflowAPI.getAvailableTransitions('c1')).resolves.toEqual(['review'])
    client.get.mockResolvedValueOnce({ data: {} })
    await expect(workflowAPI.getAvailableTransitions('c1')).resolves.toEqual([])
    expect(client.get).toHaveBeenCalledWith('/workflow/curation/c1/state')
  })

  it('validatePMID returns the first result of the batch call', async () => {
    client.post.mockResolvedValue({ data: { results: [{ pmid: '1', is_valid: true }] } })
    await expect(publicationsAPI.validatePMID('1')).resolves.toEqual({ pmid: '1', is_valid: true })
    expect(client.post).toHaveBeenCalledWith('/publications/validate', { pmids: ['1'] })
  })

  it('getPublicSummary returns null for a 404 and rethrows other failures', async () => {
    client.get.mockRejectedValueOnce({ response: { status: 404 } })
    await expect(geneSummaryAPI.getPublicSummary('g')).resolves.toBeNull()

    const serverError = { response: { status: 500 } }
    client.get.mockRejectedValueOnce(serverError)
    await expect(geneSummaryAPI.getPublicSummary('g')).rejects.toBe(serverError)
  })

  it('getPublicSummary returns the summary when found', async () => {
    client.get.mockResolvedValue({ data: { gene_symbol: 'BRCA1' } })
    await expect(geneSummaryAPI.getPublicSummary('g')).resolves.toEqual({ gene_symbol: 'BRCA1' })
  })

  it('getPendingInvitations passes the response through', async () => {
    client.get.mockResolvedValue({ data: { invitations: [], total: 0 } })
    await expect(invitationsApi.getPendingInvitations()).resolves.toEqual({
      invitations: [],
      total: 0
    })
  })

  it('invitations default export is the same object', async () => {
    const mod = await import('../invitations')
    expect(mod.default).toBe(invitationsApi)
  })

  it('auth default and named exports refer to the same API object', async () => {
    const mod = await import('../auth')
    expect(mod.default).toBe(authAPI)
    expect(mod.authApi).toBe(authAPI)
  })
})
