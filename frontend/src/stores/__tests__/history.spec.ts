import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useHistoryStore } from '@/stores/history'
import { logService } from '@/services/logService'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

describe('useHistoryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initContext creates a context once', () => {
    const store = useHistoryStore()
    store.initContext('form')
    store.initContext('form')

    expect(store.getAllContexts).toEqual(['form'])
    expect(logService.debug).toHaveBeenCalledTimes(1)
  })

  it('pushState stores deep clones and clears the redo stack', () => {
    const store = useHistoryStore()
    const before = { name: 'a', tags: ['x'] }
    const after = { name: 'b', tags: ['x'] }

    store.pushState('form', 'edit', before, after)
    before.name = 'mutated'

    expect(store.getHistorySize('form')).toBe(1)
    expect(store.canUndo('form')).toBe(true)
    expect(store.canRedo('form')).toBe(false)
    expect(store.undo('form')).toEqual({ name: 'a', tags: ['x'] })
  })

  it('pushState drops the oldest entry beyond maxHistory', () => {
    const store = useHistoryStore()
    store.maxHistory = 2

    store.pushState('c', 'one', 1, 2)
    store.pushState('c', 'two', 2, 3)
    store.pushState('c', 'three', 3, 4)

    expect(store.getHistorySize('c')).toBe(2)
    expect(store.getStateSummary('c').lastAction).toBe('three')
    expect(logService.debug).toHaveBeenCalledWith('History limit reached, removed oldest entry', {
      context: 'c'
    })
  })

  it('undo moves the entry to the redo stack and returns the previous state', () => {
    const store = useHistoryStore()
    store.pushState('c', 'edit', 'old', 'new')

    expect(store.undo('c')).toBe('old')
    expect(store.canUndo('c')).toBe(false)
    expect(store.canRedo('c')).toBe(true)
    expect(logService.info).toHaveBeenCalledWith(
      'Undo action',
      expect.objectContaining({ context: 'c', action: 'edit' })
    )
  })

  it('redo moves the entry back and returns the new state', () => {
    const store = useHistoryStore()
    store.pushState('c', 'edit', 'old', 'new')
    store.undo('c')

    expect(store.redo('c')).toBe('new')
    expect(store.canRedo('c')).toBe(false)
    expect(store.canUndo('c')).toBe(true)
  })

  it('undo and redo return null and warn when there is nothing to do', () => {
    const store = useHistoryStore()

    expect(store.undo('missing')).toBeNull()
    expect(store.redo('missing')).toBeNull()
    expect(logService.warn).toHaveBeenCalledWith('Undo called but no history available', {
      context: 'missing'
    })
    expect(logService.warn).toHaveBeenCalledWith('Redo called but no future available', {
      context: 'missing'
    })

    store.pushState('c', 'edit', 1, 2)
    expect(store.redo('c')).toBeNull()
    expect(logService.warn).toHaveBeenCalledWith('Redo called but no future available', {
      context: 'c'
    })
  })

  it('a new push invalidates the redo stack', () => {
    const store = useHistoryStore()
    store.pushState('c', 'a', 1, 2)
    store.undo('c')
    expect(store.canRedo('c')).toBe(true)

    store.pushState('c', 'b', 1, 3)

    expect(store.canRedo('c')).toBe(false)
  })

  it('uses the default context when none is given', () => {
    const store = useHistoryStore()
    store.pushState('default', 'x', 1, 2)

    expect(store.canUndo()).toBe(true)
    expect(store.getHistorySize()).toBe(1)
    expect(store.canRedo()).toBe(false)
  })

  it('canUndo, canRedo and getHistorySize are false/zero for unknown contexts', () => {
    const store = useHistoryStore()
    expect(store.canUndo('none')).toBe(false)
    expect(store.canRedo('none')).toBe(false)
    expect(store.getHistorySize('none')).toBe(0)
  })

  it('clearHistory removes a single context', () => {
    const store = useHistoryStore()
    store.pushState('a', 'x', 1, 2)
    store.pushState('b', 'x', 1, 2)

    store.clearHistory('a')

    expect(store.getAllContexts).toEqual(['b'])
  })

  it('clearAllHistory removes every context and logs the count', () => {
    const store = useHistoryStore()
    store.pushState('a', 'x', 1, 2)
    store.pushState('b', 'x', 1, 2)

    store.clearAllHistory()

    expect(store.getAllContexts).toEqual([])
    expect(logService.info).toHaveBeenCalledWith('All history cleared', { contextCount: 2 })
  })

  it('getStateSummary reports existence, sizes and last action', () => {
    const store = useHistoryStore()
    expect(store.getStateSummary('none')).toEqual({ exists: false })

    store.pushState('c', 'first', 1, 2)
    store.pushState('c', 'second', 2, 3)
    store.undo('c')

    expect(store.getStateSummary('c')).toEqual({
      exists: true,
      pastSize: 1,
      futureSize: 1,
      canUndo: true,
      canRedo: true,
      lastAction: 'first'
    })
  })

  it('getStateSummary reports a null last action for an empty context', () => {
    const store = useHistoryStore()
    store.initContext('empty')

    expect(store.getStateSummary('empty')).toMatchObject({
      exists: true,
      canUndo: false,
      lastAction: null
    })
  })
})
