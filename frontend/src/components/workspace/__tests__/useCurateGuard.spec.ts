import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCurateGuard } from '../useCurateGuard'
import { useScopesStore } from '@/stores/scopes'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

describe('useCurateGuard', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it.each([
    ['viewer', true],
    ['reviewer', true],
    ['curator', false],
    ['admin', false],
    [null, true]
  ])('role %s: denied=%s', async (role, denied) => {
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue(role as never)
    const guard = useCurateGuard(() => 's1')
    expect(guard.allowed.value).toBe(false) // nothing is allowed before the role is confirmed
    await guard.check()
    expect(guard.denied.value).toBe(denied)
    expect(guard.allowed.value).toBe(!denied)
  })

  it('denies on a 403 from the role lookup', async () => {
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockRejectedValue({ response: { status: 403 } })
    const guard = useCurateGuard(() => 's1')
    await guard.check()
    expect(guard.denied.value).toBe(true)
    expect(guard.failed.value).toBe(false)
  })

  it('fails closed with a retryable error on any other failure, and recovers on retry', async () => {
    const fetch = vi.spyOn(useScopesStore(), 'fetchUserRole').mockRejectedValue(new Error('500'))
    const guard = useCurateGuard(() => 's1')
    await guard.check()
    expect(guard.denied.value).toBe(false)
    expect(guard.failed.value).toBe(true)
    expect(guard.allowed.value).toBe(false)

    fetch.mockResolvedValue('curator' as never)
    await guard.check()
    expect(guard.failed.value).toBe(false)
    expect(guard.allowed.value).toBe(true)
  })

  it('checks only when asked, with the scope in context', async () => {
    const fetch = vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
    await useCurateGuard(() => 'scope-9').check()
    expect(fetch).toHaveBeenCalledWith('scope-9')
  })
})
