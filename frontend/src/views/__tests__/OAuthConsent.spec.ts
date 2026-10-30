import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import OAuthConsent from '@/views/OAuthConsent.vue'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
vi.mock('vue-router', () => ({ useRoute: () => ({ query: { request: 'req-1' } }) }))

const api = vi.mocked(apiClient)
const assign = vi.fn()

async function mountView() {
  const w = mount(OAuthConsent)
  await flushPromises()
  return w
}

describe('OAuthConsent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('location', { ...window.location, assign })
  })

  it('shows the client and sends the browser to the redirect it is given', async () => {
    api.get.mockResolvedValue({
      data: {
        client_name: 'Claude Code',
        redirect_uri: 'http://localhost:1/cb',
        scopes: ['read']
      }
    })
    api.post.mockResolvedValue({ data: { redirect_url: 'http://localhost:1/cb?code=c' } })
    const w = await mountView()

    expect(api.get).toHaveBeenCalledWith('/oauth/authorizations/req-1')
    expect(w.text()).toContain('Claude Code')
    expect(w.text()).toContain('read-only')
    expect(w.get('[data-test="consent-redirect"]').text()).toBe('http://localhost:1/cb')

    await w.get('[data-test="consent-allow"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/oauth/authorizations/req-1', { approve: true })
    expect(assign).toHaveBeenCalledWith('http://localhost:1/cb?code=c')
  })

  it('denies, and reports an unknown request without buttons', async () => {
    api.get.mockResolvedValueOnce({
      data: { client_name: 'X', redirect_uri: 'https://x/cb', scopes: ['read', 'write'] }
    })
    api.post.mockRejectedValue(new Error('gone'))
    const w = await mountView()
    expect(w.text()).not.toContain('read-only')
    await w.get('[data-test="consent-deny"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/oauth/authorizations/req-1', { approve: false })
    expect(w.find('[data-test="consent-error"]').exists()).toBe(true)
    expect(assign).not.toHaveBeenCalled()

    api.get.mockRejectedValueOnce(new Error('404'))
    const missing = await mountView()
    expect(missing.find('[data-test="consent-error"]').exists()).toBe(true)
    expect(missing.find('[data-test="consent-allow"]').exists()).toBe(false)
  })
})
