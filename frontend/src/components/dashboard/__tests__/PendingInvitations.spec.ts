/**
 * PendingInvitations Component Tests
 *
 * @see src/components/dashboard/PendingInvitations.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import PendingInvitations from '../PendingInvitations.vue'
import { installVisualViewport } from '../../__tests__/overlay-env'

installVisualViewport()

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

vi.mock('@/stores/invitations', async () => {
  const { reactive } = await import('vue')
  const store = reactive({
    invitations: [] as unknown[],
    pendingCount: 0,
    loading: false,
    fetchPendingInvitations: vi.fn(() => Promise.resolve()),
    acceptInvitation: vi.fn(() => Promise.resolve()),
    declineInvitation: vi.fn(() => Promise.resolve())
  })
  return { useInvitationsStore: () => store }
})

import { useInvitationsStore } from '@/stores/invitations'

interface TestInvitationsStore {
  invitations: unknown[]
  pendingCount: number
  loading: boolean
  fetchPendingInvitations: ReturnType<typeof vi.fn>
  acceptInvitation: ReturnType<typeof vi.fn>
  declineInvitation: ReturnType<typeof vi.fn>
}

interface PendingVm {
  snackbarMessage: string
  snackbarColor: string
  refreshInvitations: () => Promise<void>
  formatExpiryTime: (expiresAt: string) => string
}

const store = useInvitationsStore() as unknown as TestInvitationsStore

const invitation = {
  id: 'inv-1',
  scope_id: 'scope-1',
  scope_name: 'pathways',
  scope_display_name: 'Pathways Team',
  role: 'curator',
  inviter_name: 'Dr. Halbritter',
  // 3.5 days out, so the floored day count reads "3 days" by the time the test runs.
  expires_at: new Date(Date.now() + 3.5 * 24 * 60 * 60 * 1000).toISOString(),
  is_expired: false
}

let wrapper: VueWrapper | undefined

function mountPending() {
  wrapper = mount(PendingInvitations, { attachTo: document.body })
  return wrapper
}

function vmOf(w: VueWrapper) {
  return w.vm as unknown as PendingVm
}

function buttonWith(w: VueWrapper, text: string) {
  return w.findAll('button').find(b => b.text().includes(text))
}

describe('PendingInvitations', () => {
  beforeEach(() => {
    store.invitations = []
    store.pendingCount = 0
    store.loading = false
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  it('loads pending invitations on mount', async () => {
    mountPending()
    await flushPromises()

    expect(store.fetchPendingInvitations).toHaveBeenCalled()
  })

  it('logs a load failure on mount', async () => {
    store.fetchPendingInvitations.mockRejectedValueOnce(new Error('offline'))
    mountPending()
    await flushPromises()

    expect(logger.error).toHaveBeenCalledWith('Failed to load pending invitations', {
      error: 'offline'
    })
  })

  it('shows the empty state without invitations', () => {
    const w = mountPending()

    expect(w.text()).toContain('No pending invitations')
  })

  it('shows a spinner while loading the first time', () => {
    store.loading = true
    const w = mountPending()

    expect(w.find('.v-progress-circular').exists()).toBe(true)
  })

  it('lists invitations with role, inviter and expiry', () => {
    store.invitations = [invitation]
    store.pendingCount = 1
    const w = mountPending()

    expect(w.text()).toContain('Pathways Team')
    expect(w.text()).toContain('Role: curator')
    expect(w.text()).toContain('by Dr. Halbritter')
    expect(w.text()).toContain('Expires in 3 days')
  })

  it('marks expired invitations and disables Accept', () => {
    store.invitations = [{ ...invitation, is_expired: true }]
    const w = mountPending()

    expect(w.text()).toContain('Expired')
    expect(buttonWith(w, 'Accept')?.attributes('disabled')).toBeDefined()
  })

  it('accepts an invitation and confirms with a snackbar', async () => {
    store.invitations = [invitation]
    const w = mountPending()

    await buttonWith(w, 'Accept')?.trigger('click')
    await flushPromises()

    expect(store.acceptInvitation).toHaveBeenCalledWith('inv-1', 'scope-1')
    expect(vmOf(w).snackbarMessage).toBe('Joined Pathways Team as curator')
    expect(vmOf(w).snackbarColor).toBe('success')
  })

  it('reports a failed accept', async () => {
    store.invitations = [invitation]
    store.acceptInvitation.mockRejectedValueOnce(new Error('nope'))
    const w = mountPending()

    await buttonWith(w, 'Accept')?.trigger('click')
    await flushPromises()

    expect(vmOf(w).snackbarMessage).toBe('Failed to accept invitation')
    expect(vmOf(w).snackbarColor).toBe('error')
  })

  it('declines an invitation and reports the result', async () => {
    store.invitations = [invitation]
    const w = mountPending()

    await buttonWith(w, 'Decline')?.trigger('click')
    await flushPromises()

    expect(store.declineInvitation).toHaveBeenCalledWith('inv-1')
    expect(vmOf(w).snackbarMessage).toBe('Invitation declined')
  })

  it('reports a failed decline', async () => {
    store.invitations = [invitation]
    store.declineInvitation.mockRejectedValueOnce(new Error('nope'))
    const w = mountPending()

    await buttonWith(w, 'Decline')?.trigger('click')
    await flushPromises()

    expect(vmOf(w).snackbarMessage).toBe('Failed to decline invitation')
    expect(vmOf(w).snackbarColor).toBe('error')
  })

  it('refreshes forcibly and reports a failed refresh', async () => {
    store.invitations = [invitation]
    const w = mountPending()
    const vm = vmOf(w)

    await vm.refreshInvitations()
    expect(store.fetchPendingInvitations).toHaveBeenCalledWith({ force: true })

    store.fetchPendingInvitations.mockRejectedValueOnce(new Error('down'))
    await vm.refreshInvitations()

    expect(vm.snackbarMessage).toBe('Failed to refresh invitations')
    expect(vm.snackbarColor).toBe('error')
  })

  it.each([
    [-1000, 'expired'],
    [30 * 60 * 1000, 'soon'],
    [90 * 60 * 1000, 'in 1 hour'],
    [5 * 60 * 60 * 1000, 'in 5 hours'],
    [36 * 60 * 60 * 1000, 'in 1 day'],
    [5.5 * 24 * 60 * 60 * 1000, 'in 5 days']
  ])('formats %i ms from now as "%s"', (offset, expected) => {
    const w = mountPending()
    const expiresAt = new Date(Date.now() + offset).toISOString()

    expect(vmOf(w).formatExpiryTime(expiresAt)).toBe(expected)
  })
})
