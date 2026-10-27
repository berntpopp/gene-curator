import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AccessTokens from '@/views/AccessTokens.vue'
import { tokensAPI } from '@/api/tokens'
import { useTokensStore } from '@/stores/tokens'
import { call, vmOf } from './vm'
import type { Schema } from '@/types/api'

const { confirmMock, showError, showSuccess } = vi.hoisted(() => ({
  confirmMock: vi.fn(),
  showError: vi.fn(),
  showSuccess: vi.fn()
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))
vi.mock('@/api/tokens', () => ({
  tokensAPI: { list: vi.fn(), create: vi.fn(), revoke: vi.fn() }
}))

const api = vi.mocked(tokensAPI)
const SECRET = 'gc_pat_secret-plaintext-value'

const token = (over: Partial<Schema<'PersonalAccessTokenResponse'>> = {}) => ({
  id: 't1',
  name: 'laptop',
  token_prefix: 'gc_pat_abcde',
  scopes: ['read', 'write'],
  expires_at: '2099-01-01T00:00:00Z',
  revoked_at: null,
  last_used_at: null,
  created_at: '2026-10-01T00:00:00Z',
  ...over
})

async function mountView() {
  const w = mount(AccessTokens, { attachTo: document.body })
  await flushPromises()
  return w
}

describe('AccessTokens view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.list.mockResolvedValue([
      token(),
      token({ id: 't2', name: 'old', revoked_at: '2026-10-02T00:00:00Z' }),
      token({ id: 't3', name: 'ro', scopes: ['read'], expires_at: '2020-01-01T00:00:00Z' })
    ])
  })

  it('lists tokens with access, status and a revoke button only for live ones', async () => {
    const w = await mountView()
    const rows = w.findAll('[data-test="token-row"]')
    expect(rows).toHaveLength(3)
    expect(rows[0]!.text()).toContain('Read and write')
    expect(rows[0]!.text()).toContain('Never')
    expect(rows[0]!.find('button').text()).toBe('Revoke')
    expect(rows[1]!.text()).toContain('Revoked')
    expect(rows[2]!.text()).toContain('Read-only')
    expect(rows[2]!.text()).toContain('Expired')
  })

  it('creates a token, shows the plaintext once and forgets it on Done', async () => {
    api.create.mockResolvedValue({ ...token({ id: 'new', name: 'cli' }), token: SECRET })
    const w = await mountView()
    const vm = vmOf(w)
    vm.name = ' cli '
    vm.readOnly = true
    await call(vm, 'create')
    await flushPromises()

    const sent = api.create.mock.calls[0]![0]
    expect(sent.name).toBe('cli')
    expect(sent.scopes).toEqual(['read'])
    const days = (new Date(sent.expires_at).getTime() - Date.now()) / 86_400_000
    expect(Math.round(days)).toBe(90) // default expiry
    expect(vm.showToken).toBe(true)
    expect(vm.plaintext).toBe(SECRET)
    expect(vm.mcpCommand).toMatch(
      new RegExp(
        `^claude mcp add --transport http gene-curator \\S+/mcp --header "Authorization: Bearer ${SECRET}"$`
      )
    )
    expect(useTokensStore().tokens[0]).not.toHaveProperty('token')

    call(vm, 'closeToken')
    expect(vm.plaintext).toBe('')
    expect(vm.showToken).toBe(false)
    w.unmount()
  })

  it('does not create without a name and reports API errors', async () => {
    const w = await mountView()
    const vm = vmOf(w)
    await call(vm, 'create')
    expect(api.create).not.toHaveBeenCalled()

    api.create.mockRejectedValue({ response: { data: { detail: 'nope' } } })
    vm.name = 'x'
    await call(vm, 'create')
    expect(showError).toHaveBeenCalledWith('nope')
  })

  it('copies the token and falls back to a hint when the clipboard fails', async () => {
    const writeText = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(new Error())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const w = await mountView()
    const vm = vmOf(w)
    vm.plaintext = SECRET
    await call(vm, 'copy', SECRET)
    expect(writeText).toHaveBeenCalledWith(SECRET)
    expect(showSuccess).toHaveBeenCalledWith('Copied')
    await call(vm, 'copy', SECRET)
    expect(showError).toHaveBeenCalled()
  })

  it('revokes after confirmation and reloads the list', async () => {
    const w = await mountView()
    confirmMock.mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    await w.find('[data-test="token-row"] button').trigger('click')
    await flushPromises()
    expect(api.revoke).not.toHaveBeenCalled()

    await w.find('[data-test="token-row"] button').trigger('click')
    await flushPromises()
    expect(api.revoke).toHaveBeenCalledWith('t1')
    expect(api.list).toHaveBeenCalledTimes(2)
    expect(showSuccess).toHaveBeenCalledWith('Token revoked')

    api.revoke.mockRejectedValue(new Error('down'))
    confirmMock.mockResolvedValueOnce(true)
    await w.find('[data-test="token-row"] button').trigger('click')
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('down')
  })

  it('shows a load error', async () => {
    api.list.mockRejectedValue(new Error('offline'))
    const w = await mountView()
    expect(w.text()).toContain('offline')
  })
})
