import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { errorMessage } from '../apiError'
import { useAssignmentsStore } from '../assignments'
import { assignmentsAPI } from '@/api'

vi.mock('@/api', () => ({ assignmentsAPI: { getAssignments: vi.fn() } }))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const reject = (data: unknown, message = 'Request failed with status code 409') =>
  Object.assign(new Error(message), { response: { status: 409, data } })

describe('errorMessage', () => {
  it('prefers a string detail (e.g. a 409 conflict explanation)', () => {
    expect(errorMessage(reject({ detail: 'Gene already assigned' }), 'fallback')).toBe(
      'Gene already assigned'
    )
  })

  it('uses the first validation message for FastAPI 422 arrays, never [object Object]', () => {
    const err = reject({ detail: [{ msg: 'field required', loc: ['body', 'x'] }] })
    expect(errorMessage(err, 'fallback')).toBe('field required')
  })

  it('falls back to the axios message, then to the fallback', () => {
    expect(errorMessage(reject({}), 'fallback')).toBe('Request failed with status code 409')
    expect(errorMessage(reject({ detail: [] }, ''), 'fallback')).toBe('fallback')
    expect(errorMessage(undefined, 'fallback')).toBe('fallback')
    expect(errorMessage('weird', 'fallback')).toBe('fallback')
  })
})

describe('stores use errorMessage', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows the server detail of a 409 and the first msg of a 422', async () => {
    const store = useAssignmentsStore()
    vi.mocked(assignmentsAPI.getAssignments).mockRejectedValueOnce(
      reject({ detail: 'Gene already assigned' })
    )
    await expect(store.fetchAssignments()).rejects.toBeDefined()
    expect(store.error).toBe('Gene already assigned')

    vi.mocked(assignmentsAPI.getAssignments).mockRejectedValueOnce(
      reject({ detail: [{ msg: 'bad priority' }] })
    )
    await expect(store.fetchAssignments()).rejects.toBeDefined()
    expect(store.error).toBe('bad priority')
  })
})
