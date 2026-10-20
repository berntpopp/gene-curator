import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useValidation } from '../useValidation'

const store = {
  validateHGNC: vi.fn(),
  validatePubMed: vi.fn(),
  validateHPO: vi.fn()
}

vi.mock('@/stores/externalValidation', () => ({
  useExternalValidationStore: () => store
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

describe('useValidation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('rejects unknown validator types', () => {
    expect(() => useValidation('bogus' as never)).toThrow('Invalid validator: bogus')
  })

  it('validate() dispatches to the HGNC store method and stores the result', async () => {
    store.validateHGNC.mockResolvedValue({ is_valid: true, approved_symbol: 'BRCA1' })
    const { validate, result, isValidating, error } = useValidation('hgnc')

    const outcome = await validate('BRCA1')

    expect(store.validateHGNC).toHaveBeenCalledWith('BRCA1')
    expect(outcome).toEqual({ is_valid: true, approved_symbol: 'BRCA1' })
    expect(result.value).toEqual(outcome)
    expect(isValidating.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('validate() dispatches to PubMed and HPO store methods', async () => {
    store.validatePubMed.mockResolvedValue({ is_valid: true })
    store.validateHPO.mockResolvedValue({ is_valid: false })

    await useValidation('pubmed').validate('12345')
    await useValidation('hpo').validate('HP:0000001')

    expect(store.validatePubMed).toHaveBeenCalledWith('12345')
    expect(store.validateHPO).toHaveBeenCalledWith('HP:0000001')
  })

  it('validate() without argument uses the current value and returns null when empty', async () => {
    store.validateHGNC.mockResolvedValue({ is_valid: true })
    const { value, validate, result } = useValidation('hgnc')

    expect(await validate()).toBeNull()
    expect(store.validateHGNC).not.toHaveBeenCalled()
    expect(result.value).toBeNull()

    value.value = 'TP53'
    await validate()
    expect(store.validateHGNC).toHaveBeenCalledWith('TP53')
  })

  it('validate() captures errors and returns null', async () => {
    store.validateHGNC.mockRejectedValue(new Error('network down'))
    const { validate, error, isValidating } = useValidation('hgnc')

    expect(await validate('BRCA1')).toBeNull()
    expect(error.value).toBe('network down')
    expect(isValidating.value).toBe(false)
  })

  it('validate() falls back to a generic message for non-Error rejections', async () => {
    store.validateHGNC.mockRejectedValue('oops')
    const { validate, error } = useValidation('hgnc')

    await validate('BRCA1')
    expect(error.value).toBe('Validation failed')
  })

  it('automatic validation is debounced by 500ms and skips short values', async () => {
    store.validateHGNC.mockResolvedValue({ is_valid: true })
    const { value, result } = useValidation('hgnc')

    value.value = 'B'
    await vi.advanceTimersByTimeAsync(600)
    expect(store.validateHGNC).not.toHaveBeenCalled()

    value.value = 'BRCA'
    await vi.advanceTimersByTimeAsync(499)
    expect(store.validateHGNC).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(10)

    expect(store.validateHGNC).toHaveBeenCalledTimes(1)
    expect(store.validateHGNC).toHaveBeenCalledWith('BRCA')
    expect(result.value).toEqual({ is_valid: true })
  })

  it('debounced validation records errors without throwing', async () => {
    store.validateHGNC.mockRejectedValue(new Error('timeout'))
    const { value, error } = useValidation('hgnc')

    value.value = 'BRCA1'
    await vi.advanceTimersByTimeAsync(600)

    expect(error.value).toBe('timeout')
  })

  it('clearing the value resets the result without calling the store', async () => {
    store.validateHGNC.mockResolvedValue({ is_valid: true })
    const { value, result } = useValidation('hgnc')

    value.value = 'BRCA1'
    await vi.advanceTimersByTimeAsync(600)
    expect(result.value).not.toBeNull()

    value.value = 'X'
    await vi.advanceTimersByTimeAsync(600)
    expect(result.value).toBeNull()
  })

  it('reset() clears value, result and error', async () => {
    store.validateHGNC.mockRejectedValue(new Error('bad'))
    const { value, validate, reset, error, result, isValidating } = useValidation('hgnc')

    value.value = 'BRCA1'
    await validate()
    reset()

    expect(value.value).toBe('')
    expect(result.value).toBeNull()
    expect(error.value).toBeNull()
    expect(isValidating.value).toBe(false)
  })
})
