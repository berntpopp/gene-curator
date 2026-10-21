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
    expect(guard.denied.value).toBe(false) // not decided yet
    await guard.check()
    expect(guard.denied.value).toBe(denied)
  })

  it('lets the page through when the role cannot be read (the server still refuses)', async () => {
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockRejectedValue(new Error('x'))
    const guard = useCurateGuard(() => 's1')
    await guard.check()
    expect(guard.denied.value).toBe(false)
  })

  it('checks only when asked, with the scope in context', async () => {
    const fetch = vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
    await useCurateGuard(() => 'scope-9').check()
    expect(fetch).toHaveBeenCalledWith('scope-9')
  })
})
