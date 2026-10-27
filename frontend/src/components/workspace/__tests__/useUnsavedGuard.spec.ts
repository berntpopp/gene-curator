import { describe, it, expect, vi, afterEach } from 'vitest'
import { createApp, defineComponent, h, ref } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'

const confirm = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))

import { useUnsavedGuard, reloadDiscardingChanges } from '../useUnsavedGuard'

const dirty = ref(false)
const mounted: { unmount: () => void }[] = []

async function setup() {
  const Page = defineComponent({
    setup() {
      useUnsavedGuard(dirty)
      return () => h('div')
    }
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/edit', component: Page },
      { path: '/other', component: { render: () => h('p') } }
    ]
  })
  await router.push('/edit')
  const app = createApp({ render: () => h(RouterView) })
  app.use(router).mount(document.createElement('div'))
  mounted.push(app)
  return { router, app }
}

afterEach(() => {
  mounted.splice(0).forEach(a => a.unmount())
  dirty.value = false
  confirm.mockReset()
  document.body.innerHTML = ''
})

describe('useUnsavedGuard', () => {
  // #469: a focused cell's typed text commits on blur, which is what makes the page dirty
  const typing = () => {
    const input = document.body.appendChild(document.createElement('input'))
    input.addEventListener('blur', () => (dirty.value = true))
    input.focus()
  }

  it('commits the focused field before deciding to ask on route leave', async () => {
    confirm.mockResolvedValue(false)
    const { router } = await setup()
    typing()
    await router.push('/other')
    expect(confirm).toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/edit')
  })

  it('commits the focused field before deciding to warn on reload', async () => {
    await setup()
    typing()
    const e = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(e)
    expect(e.defaultPrevented).toBe(true)
  })

  it('lets a clean page go without asking', async () => {
    const { router } = await setup()
    await router.push('/other')
    expect(confirm).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/other')
  })

  it('asks before leaving with unsaved changes and stays when declined', async () => {
    confirm.mockResolvedValue(false)
    const { router } = await setup()
    dirty.value = true
    await router.push('/other')
    expect(confirm).toHaveBeenCalledWith(expect.objectContaining({ destructive: true }))
    expect(router.currentRoute.value.path).toBe('/edit')
  })

  it('leaves when the user confirms', async () => {
    confirm.mockResolvedValue(true)
    const { router } = await setup()
    dirty.value = true
    await router.push('/other')
    expect(router.currentRoute.value.path).toBe('/other')
  })

  it('warns on tab close or reload only while dirty, and detaches on unmount', async () => {
    const { app } = await setup()
    const fire = () => {
      const e = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(fire()).toBe(false)
    dirty.value = true
    expect(fire()).toBe(true)
    app.unmount()
    expect(fire()).toBe(false)
  })

  it('reloads without the leave prompt once the user chose to discard (conflict)', async () => {
    const reload = vi.fn()
    vi.stubGlobal('location', { ...window.location, reload })
    await setup()
    dirty.value = true
    reloadDiscardingChanges()
    const e = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(e)
    expect(e.defaultPrevented).toBe(false)
    expect(reload).toHaveBeenCalledOnce()
    vi.unstubAllGlobals()
  })
})
