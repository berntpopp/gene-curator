/**
 * UserSearchAutocomplete Component Tests
 *
 * @see src/components/common/UserSearchAutocomplete.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import UserSearchAutocomplete from '../UserSearchAutocomplete.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

const scope = vi.hoisted(() => ({ searchUsersForInvite: vi.fn() }))
vi.mock('@/services/scopeService', () => ({ scopeService: scope }))

interface SearchVm {
  searchResults: { id: string; displayName: string }[]
  searching: boolean
  onSearchUpdate: (query: string) => void
  clearSelection: () => void
  getInitials: (name: string | null | undefined) => string
}

const users = [
  { id: 'u1', name: 'Ada Lovelace', email: 'ada@example.org', institution: 'Berlin' },
  { id: 'u2', name: null, email: 'grace@example.org', institution: null },
  { id: 'u3', name: 'Excluded Person', email: 'ex@example.org' }
]

let wrapper: VueWrapper | undefined

interface SearchOverrides {
  scopeId?: string
  excludeUserIds?: string[]
  modelValue?: { id: string; name: string | null; email: string; displayName: string } | null
}

function mountSearch(overrides: SearchOverrides = {}) {
  wrapper = mount(UserSearchAutocomplete, { props: { scopeId: 'scope-1', ...overrides } })
  return wrapper
}

function vmOf(w: VueWrapper) {
  return w.vm as unknown as SearchVm
}

describe('UserSearchAutocomplete', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    scope.searchUsersForInvite.mockResolvedValue(users)
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('does not search for queries shorter than two characters', () => {
    const vm = vmOf(mountSearch())

    vm.onSearchUpdate('a')
    vi.advanceTimersByTime(500)

    expect(scope.searchUsersForInvite).not.toHaveBeenCalled()
    expect(vm.searchResults).toEqual([])
  })

  it('debounces input and searches the scope once', async () => {
    const vm = vmOf(mountSearch())

    vm.onSearchUpdate('j')
    vm.onSearchUpdate('jo')
    vm.onSearchUpdate('john')
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(scope.searchUsersForInvite).toHaveBeenCalledTimes(1)
    expect(scope.searchUsersForInvite).toHaveBeenCalledWith('scope-1', 'john')
  })

  it('shows a loading indicator while the search is running', async () => {
    scope.searchUsersForInvite.mockReturnValue(new Promise(() => {}))
    const w = mountSearch()
    vmOf(w).onSearchUpdate('ada')
    vi.advanceTimersByTime(300)
    await w.vm.$nextTick()

    expect(vmOf(w).searching).toBe(true)
    expect(w.find('.v-progress-circular').exists()).toBe(true)
  })

  it('maps results to display names and drops excluded users', async () => {
    const vm = vmOf(mountSearch({ scopeId: 'scope-1', excludeUserIds: ['u3'] }))

    vm.onSearchUpdate('ada')
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(vm.searchResults.map(r => r.displayName)).toEqual(['Ada Lovelace', 'grace@example.org'])
    expect(vm.searching).toBe(false)
  })

  it('clears results and logs when the search fails', async () => {
    scope.searchUsersForInvite.mockRejectedValue(new Error('offline'))
    const vm = vmOf(mountSearch())

    vm.onSearchUpdate('ada')
    vi.advanceTimersByTime(300)
    await flushPromises()

    expect(vm.searchResults).toEqual([])
    expect(logger.error).toHaveBeenCalledWith(
      'User search failed',
      expect.objectContaining({ query: 'ada', error: 'offline' })
    )
  })

  it('clears the selection and emits null', () => {
    const w = mountSearch()
    vmOf(w).clearSelection()

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([null])
  })

  it('shows the selected user as a chip and clears it on close', async () => {
    const w = mountSearch({
      scopeId: 'scope-1',
      modelValue: { id: 'u1', name: 'Ada Lovelace', email: 'ada@example.org', displayName: 'Ada' }
    })
    await flushPromises()

    expect(w.text()).toContain('Ada Lovelace')
    await w.find('.v-chip__close').trigger('click')

    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([null])
  })

  it('resets results when the scope changes', async () => {
    const w = mountSearch()
    const vm = vmOf(w)
    vm.onSearchUpdate('ada')
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(vm.searchResults.length).toBeGreaterThan(0)

    await w.setProps({ scopeId: 'scope-2' })

    expect(vm.searchResults).toEqual([])
  })

  it.each([
    ['Ada Lovelace', 'AL'],
    ['Plato', 'P'],
    ['', '?'],
    [null, '?']
  ])('derives initials for %j', (name, expected) => {
    expect(vmOf(mountSearch()).getInitials(name)).toBe(expected)
  })
})
