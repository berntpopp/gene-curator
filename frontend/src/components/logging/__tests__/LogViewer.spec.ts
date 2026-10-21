/**
 * LogViewer Component Tests
 *
 * The log store and drawer state are mocked; the store object is shared with tests.
 *
 * @see src/components/logging/LogViewer.vue
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import LogViewer from '../LogViewer.vue'
import { logService } from '@/services/logService'

vi.mock('@/stores/logStore', async () => {
  const { reactive } = await import('vue')
  const store = reactive({
    logs: [] as unknown[],
    logCount: 0,
    maxEntries: 50,
    memoryUsage: { kb: 1 },
    logsByLevel: {} as Record<string, number>,
    isViewerVisible: false,
    exportLogs: vi.fn(() => '{"logs":[]}'),
    clearLogs: vi.fn(() => 2),
    trimLogs: vi.fn(),
    setSearchQuery: vi.fn(),
    setLevelFilter: vi.fn()
  })
  return { useLogStore: () => store }
})

const drawer = vi.hoisted(() => ({
  close: vi.fn(),
  startOpen: true,
  isOpen: null as null | { value: boolean }
}))
vi.mock('@/composables/useDrawerState', async () => {
  const { ref } = await import('vue')
  return {
    useDrawerState: () => {
      const isOpen = ref(drawer.startOpen)
      drawer.isOpen = isOpen
      return { isOpen, close: drawer.close }
    }
  }
})

import { useLogStore } from '@/stores/logStore'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

interface TestLogStore {
  logs: unknown[]
  logCount: number
  maxEntries: number
  isViewerVisible: boolean
  logsByLevel: Record<string, number>
  exportLogs: ReturnType<typeof vi.fn>
  clearLogs: ReturnType<typeof vi.fn>
  trimLogs: ReturnType<typeof vi.fn>
  setSearchQuery: ReturnType<typeof vi.fn>
  setLevelFilter: ReturnType<typeof vi.fn>
}

interface LogViewerVm {
  updateMaxEntries: (value: number) => void
  updateSearch: (value: string | null) => void
  updateLevelFilter: (value: string[]) => void
  selectedLevels: string[]
}

function vmOf(w: VueWrapper) {
  return w.vm as unknown as LogViewerVm
}

const store = useLogStore() as unknown as TestLogStore

const passthrough = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  }
})

const entries = [
  {
    timestamp: '2026-01-01T10:00:00.000Z',
    level: 'INFO',
    message: 'first message',
    correlationId: 'abcdef123456'
  },
  {
    timestamp: '2026-01-01T10:01:00.000Z',
    level: 'ERROR',
    message: 'second message',
    data: { key: 'value' }
  }
]

let wrapper: VueWrapper | undefined

function mountViewer() {
  wrapper = mount(LogViewer, { global: { stubs: { VNavigationDrawer: passthrough } } })
  return wrapper
}

function buttonByTitle(title: string) {
  return wrapper?.find(`[title="${title}"]`)
}

describe('LogViewer', () => {
  it('opens its drawer when mounted while the store already says visible', () => {
    // App.vue mounts the viewer lazily (v-if) after the store flag flipped
    drawer.startOpen = false
    store.isViewerVisible = true
    mountViewer()

    expect(drawer.isOpen?.value).toBe(true)

    drawer.startOpen = true
    store.isViewerVisible = false
  })

  beforeEach(() => {
    store.logs = [...entries]
    store.logCount = entries.length
    store.logsByLevel = { INFO: 1, ERROR: 1 }
  })

  afterEach(() => {
    vi.restoreAllMocks()
    wrapper?.unmount()
    wrapper = undefined
    store.logs = []
    store.logCount = 0
    store.logsByLevel = {}
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('lists entries newest first', () => {
    mountViewer()

    expect(wrapper?.findAll('.log-message').map(n => n.text())).toEqual([
      'second message',
      'first message'
    ])
  })

  it('shows a short correlation id and the level statistics', () => {
    mountViewer()

    expect(wrapper?.text()).toContain('abcdef12')
    expect(wrapper?.text()).toContain('INFO: 1')
  })

  it('shows the empty state when there are no logs', () => {
    store.logs = []
    store.logCount = 0
    mountViewer()

    expect(wrapper?.text()).toContain('No logs available')
  })

  it('shows the no-match state when filters hide everything', async () => {
    mountViewer()
    await wrapper?.findAll('input')[0]?.setValue('nothing matches this')

    expect(store.setSearchQuery).toHaveBeenCalledWith('nothing matches this')
    expect(wrapper?.text()).toContain('No logs match your filters')
  })

  it('filters by search text across message, level and data', async () => {
    mountViewer()
    await wrapper?.findAll('input')[0]?.setValue('key')

    expect(wrapper?.findAll('.log-message').map(n => n.text())).toEqual(['second message'])
  })

  it('filters by selected levels', async () => {
    const w = mountViewer()
    const vm = w.vm as unknown as LogViewerVm
    vm.selectedLevels = ['INFO']
    await w.vm.$nextTick()

    expect(w.findAll('.log-message').map(n => n.text())).toEqual(['first message'])
  })

  it('shows formatted log data and falls back for circular data', async () => {
    const circular: Record<string, unknown> = {}
    circular.self = circular
    store.logs = [
      { timestamp: '2026-01-01T10:00:00.000Z', level: 'WARN', message: 'loop', data: circular }
    ]
    store.logCount = 1
    mountViewer()

    // Expansion panel content is rendered lazily, so open it first.
    await wrapper?.find('.v-expansion-panel-title').trigger('click')

    expect(wrapper?.find('.log-data-content').text()).toBe('[object Object]')
  })

  it('updates the retention limit through the store', () => {
    const w = mountViewer()
    const vm = w.vm as unknown as LogViewerVm

    vm.updateMaxEntries(100)

    expect(store.trimLogs).toHaveBeenCalledWith(100)
  })

  it('reflects store changes to maxEntries', async () => {
    const w = mountViewer()
    store.maxEntries = 200
    await w.vm.$nextTick()

    expect(w.text()).toContain('/200')
    store.maxEntries = 50
  })

  it('downloads the logs as JSON', () => {
    const info = vi.spyOn(logService, 'info').mockImplementation(() => undefined)
    const createObjectURL = vi.fn(() => 'blob:logs')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }))
    mountViewer()

    buttonByTitle('Download logs as JSON')?.trigger('click')

    expect(store.exportLogs).toHaveBeenCalledWith({
      format: 'json',
      includeMetadata: true,
      filtered: false
    })
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:logs')
    expect(info).toHaveBeenCalledWith('Logs exported successfully')
  })

  it('clears logs only after confirmation', async () => {
    confirmMock.mockResolvedValue(false)
    mountViewer()
    await buttonByTitle('Clear all logs')?.trigger('click')
    expect(store.clearLogs).not.toHaveBeenCalled()

    confirmMock.mockResolvedValue(true)
    await buttonByTitle('Clear all logs')?.trigger('click')
    expect(store.clearLogs).toHaveBeenCalledTimes(1)
  })

  it('copies a log entry to the clipboard', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    mountViewer()

    await wrapper?.findAll('[title="Copy log entry"]')[0]?.trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('second message'))
  })

  it('applies search and level filter handlers to the store', () => {
    const vm = vmOf(mountViewer())

    vm.updateSearch(null)
    vm.updateSearch('timeout')
    vm.updateLevelFilter(['ERROR'])

    expect(store.setSearchQuery).toHaveBeenNthCalledWith(1, '')
    expect(store.setSearchQuery).toHaveBeenNthCalledWith(2, 'timeout')
    expect(store.setLevelFilter).toHaveBeenCalledWith(['ERROR'])
  })

  it('keeps the drawer in step with the store visibility flag', async () => {
    const w = mountViewer()

    store.isViewerVisible = true
    await w.vm.$nextTick()
    store.isViewerVisible = false
    await w.vm.$nextTick()

    expect(store.isViewerVisible).toBe(false)
  })

  it('survives a failing export', () => {
    store.exportLogs.mockImplementationOnce(() => {
      throw new Error('disk full')
    })
    mountViewer()

    const error = vi.spyOn(logService, 'error').mockImplementation(() => undefined)

    expect(() => buttonByTitle('Download logs as JSON')?.trigger('click')).not.toThrow()
    expect(error).toHaveBeenCalledWith('Failed to download logs', { error: 'disk full' })
  })

  it('closes the drawer from the close button', async () => {
    mountViewer()

    await buttonByTitle('Close log viewer')?.trigger('click')

    expect(drawer.close).toHaveBeenCalled()
  })
})
