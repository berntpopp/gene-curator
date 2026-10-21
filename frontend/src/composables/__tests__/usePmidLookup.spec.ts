import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createApp, defineComponent, h } from 'vue'

const api = vi.hoisted(() => ({ validatePMIDs: vi.fn() }))
vi.mock('@/api/publications', () => ({ publicationsAPI: api }))

import { usePmidLookup } from '../usePmidLookup'

function setup() {
  let lookup!: ReturnType<typeof usePmidLookup>
  const app = createApp(
    defineComponent({
      setup() {
        lookup = usePmidLookup()
        return () => h('div')
      }
    })
  )
  app.mount(document.createElement('div'))
  return { lookup, app }
}

const found = (pmid: string) => ({
  results: [
    {
      pmid,
      is_valid: true,
      publication: { pmid, title: 'A paper', authors: ['Smith J', 'Doe A'], year: 2019 }
    }
  ]
})

beforeEach(() => {
  vi.useFakeTimers()
  api.validatePMIDs.mockReset()
})
afterEach(() => vi.useRealTimers())

describe('usePmidLookup', () => {
  it('leaves an empty cell alone and rejects non-digits without a request', async () => {
    const { lookup } = setup()
    lookup.check(0, '')
    lookup.check(1, 'abc')
    lookup.check(2, '1234567890')
    await vi.advanceTimersByTimeAsync(1000)
    expect(api.validatePMIDs).not.toHaveBeenCalled()
    expect(lookup.statusOf('abc')).toBe('invalid')
    expect(lookup.statusOf('1234567890')).toBe('invalid')
    expect(lookup.statusOf('')).toBe('idle')
  })

  it('looks the PMID up after a debounce and keeps the citation', async () => {
    api.validatePMIDs.mockResolvedValue(found('31000001'))
    const { lookup } = setup()
    lookup.check(0, 'PMID: 31000001')
    expect(lookup.statusOf('31000001')).toBe('loading')
    await vi.advanceTimersByTimeAsync(299)
    expect(api.validatePMIDs).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(10)
    expect(api.validatePMIDs).toHaveBeenCalledWith(['31000001'], expect.any(AbortSignal))
    expect(lookup.statusOf('31000001')).toBe('found')
    expect(lookup.resultOf('31000001')).toMatchObject({
      title: 'A paper',
      citation: 'Smith et al. 2019'
    })
  })

  it('debounces quick re-blurs into one request', async () => {
    api.validatePMIDs.mockResolvedValue(found('2'))
    const { lookup } = setup()
    lookup.check(0, '1')
    lookup.check(0, '2')
    await vi.advanceTimersByTimeAsync(400)
    expect(api.validatePMIDs).toHaveBeenCalledTimes(1)
    expect(api.validatePMIDs).toHaveBeenCalledWith(['2'], expect.any(AbortSignal))
  })

  it('aborts the previous request for the same cell and ignores its late answer', async () => {
    let first!: (v: unknown) => void
    api.validatePMIDs
      .mockImplementationOnce(() => new Promise(r => (first = r)))
      .mockResolvedValueOnce(found('22'))
    const { lookup } = setup()
    lookup.check(0, '11')
    await vi.advanceTimersByTimeAsync(300)
    const signal = api.validatePMIDs.mock.calls[0]![1] as AbortSignal
    lookup.check(0, '22')
    expect(signal.aborted).toBe(true)
    await vi.advanceTimersByTimeAsync(300)
    first(found('11'))
    await vi.advanceTimersByTimeAsync(0)
    expect(lookup.statusOf('11')).not.toBe('found')
    expect(lookup.statusOf('22')).toBe('found')
  })

  it('marks an unknown PMID as not found and does not look it up twice', async () => {
    api.validatePMIDs.mockResolvedValue({
      results: [{ pmid: '99', is_valid: false, error: 'Publication not found: 99' }]
    })
    const { lookup } = setup()
    lookup.check(0, '99')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.statusOf('99')).toBe('notfound')
    lookup.check(1, '99')
    await vi.advanceTimersByTimeAsync(300)
    expect(api.validatePMIDs).toHaveBeenCalledTimes(1)
  })

  it('reports a failed request as an error, which does not block', async () => {
    api.validatePMIDs.mockRejectedValue(new Error('offline'))
    const { lookup } = setup()
    lookup.check(0, '5')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.statusOf('5')).toBe('error')
    expect(lookup.hasUnknown(['5'])).toBe(false)
  })

  it('knows which of a set of PMIDs are unknown', async () => {
    api.validatePMIDs.mockResolvedValue({
      results: [{ pmid: '9', is_valid: false, error: 'Publication not found: 9' }]
    })
    const { lookup } = setup()
    lookup.check(0, '9')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.hasUnknown(['1', '9'])).toBe(true)
    expect(lookup.hasUnknown(['1'])).toBe(false)
  })

  it('cancels pending work when the component unmounts', async () => {
    const { lookup, app } = setup()
    lookup.check(0, '7')
    app.unmount()
    await vi.advanceTimersByTimeAsync(1000)
    expect(api.validatePMIDs).not.toHaveBeenCalled()
  })

  it('treats "not found or invalid response" from Europe PMC as not found', async () => {
    api.validatePMIDs.mockResolvedValue({
      results: [{ pmid: '8', is_valid: false, error: 'Publication not found or invalid response' }]
    })
    const { lookup } = setup()
    lookup.check(0, '8')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.statusOf('8')).toBe('notfound')
  })

  it('does not call a timeout or 5xx from Europe PMC "not found": error, retried, never blocking', async () => {
    api.validatePMIDs
      .mockResolvedValueOnce({
        results: [{ pmid: '6', is_valid: false, error: 'API error: HTTP 503' }]
      })
      .mockResolvedValueOnce(found('6'))
    const { lookup } = setup()
    lookup.check(0, '6')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.statusOf('6')).toBe('error')
    expect(lookup.hasUnknown(['6'])).toBe(false)
    lookup.check(0, '6') // not cached: the next blur asks again
    await vi.advanceTimersByTimeAsync(300)
    expect(api.validatePMIDs).toHaveBeenCalledTimes(2)
    expect(lookup.statusOf('6')).toBe('found')
  })

  it('resets a lookup that was cancelled mid-flight to idle instead of leaving it loading', async () => {
    api.validatePMIDs.mockImplementation(() => new Promise(() => {}))
    const { lookup } = setup()
    lookup.check('row-a', '31')
    await vi.advanceTimersByTimeAsync(300)
    expect(lookup.statusOf('31')).toBe('loading')
    lookup.cancel('row-a')
    expect(lookup.statusOf('31')).toBe('idle')
  })

  it('does not abort another cell when one is cancelled', async () => {
    api.validatePMIDs.mockImplementation(() => new Promise(() => {}))
    const { lookup } = setup()
    lookup.check('row-a', '41')
    lookup.check('row-b', '42')
    await vi.advanceTimersByTimeAsync(300)
    const [a, b] = api.validatePMIDs.mock.calls.map(c => c[1] as AbortSignal)
    lookup.cancel('row-a')
    expect(a!.aborted).toBe(true)
    expect(b!.aborted).toBe(false)
    expect(lookup.statusOf('42')).toBe('loading')
  })
})
