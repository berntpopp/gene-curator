import { describe, it, expect, vi, beforeEach } from 'vitest'

const historyStore = vi.hoisted(() => ({
  initContext: vi.fn(),
  canUndo: vi.fn(),
  canRedo: vi.fn(),
  getHistorySize: vi.fn(),
  pushState: vi.fn(),
  undo: vi.fn(),
  redo: vi.fn(),
  clearHistory: vi.fn(),
  getStateSummary: vi.fn()
}))

vi.mock('@/stores/history', () => ({
  useHistoryStore: () => historyStore
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

import { useHistory } from '../useHistory'
import { logService } from '@/services/logService'

describe('useHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    historyStore.canUndo.mockReturnValue(true)
    historyStore.canRedo.mockReturnValue(false)
    historyStore.getHistorySize.mockReturnValue(4)
  })

  it('initialises its context and exposes reactive button state', () => {
    const { canUndo, canRedo, historySize } = useHistory('form-1')

    expect(historyStore.initContext).toHaveBeenCalledWith('form-1')
    expect(canUndo.value).toBe(true)
    expect(canRedo.value).toBe(false)
    expect(historySize.value).toBe(4)
    expect(historyStore.canUndo).toHaveBeenCalledWith('form-1')
  })

  it('recordAction pushes changed states and skips identical ones', () => {
    const { recordAction } = useHistory<{ a: number }>('form-1')

    recordAction('edit', { a: 1 }, { a: 1 })
    expect(historyStore.pushState).not.toHaveBeenCalled()

    recordAction('edit', { a: 1 }, { a: 2 })
    expect(historyStore.pushState).toHaveBeenCalledWith('form-1', 'edit', { a: 1 }, { a: 2 })
  })

  it('undo returns the previous state and applies it', () => {
    historyStore.undo.mockReturnValue({ a: 1 })
    const applyState = vi.fn()
    const { undo } = useHistory<{ a: number }>('form-1', applyState)

    expect(undo()).toEqual({ a: 1 })
    expect(applyState).toHaveBeenCalledWith({ a: 1 })
  })

  it('undo returns null and does not apply when there is nothing to undo', () => {
    historyStore.undo.mockReturnValue(null)
    const applyState = vi.fn()
    const { undo } = useHistory('form-1', applyState)

    expect(undo()).toBeNull()
    expect(applyState).not.toHaveBeenCalled()
  })

  it('redo returns the next state and applies it', () => {
    historyStore.redo.mockReturnValue({ a: 3 })
    const applyState = vi.fn()
    const { redo } = useHistory<{ a: number }>('form-1', applyState)

    expect(redo()).toEqual({ a: 3 })
    expect(applyState).toHaveBeenCalledWith({ a: 3 })
  })

  it('redo returns null when nothing to redo', () => {
    historyStore.redo.mockReturnValue(null)
    const { redo } = useHistory('form-1', vi.fn())

    expect(redo()).toBeNull()
  })

  it('logs an error but still returns state when applyState throws on undo or redo', () => {
    historyStore.undo.mockReturnValue({ a: 1 })
    historyStore.redo.mockReturnValue({ a: 2 })
    const applyState = vi.fn(() => {
      throw new Error('apply failed')
    })
    const { undo, redo } = useHistory('form-1', applyState)

    expect(undo()).toEqual({ a: 1 })
    expect(redo()).toEqual({ a: 2 })
    expect(logService.error).toHaveBeenCalledWith(
      'Failed to apply undo state',
      expect.objectContaining({ context: 'form-1', error: 'apply failed' })
    )
    expect(logService.error).toHaveBeenCalledWith(
      'Failed to apply redo state',
      expect.objectContaining({ context: 'form-1', error: 'apply failed' })
    )
  })

  it('clearHistory and getStateSummary delegate to the store', () => {
    const summary = { canUndo: true, canRedo: false, lastAction: 'edit' }
    historyStore.getStateSummary.mockReturnValue(summary)
    const { clearHistory, getStateSummary } = useHistory('form-1')

    clearHistory()
    expect(historyStore.clearHistory).toHaveBeenCalledWith('form-1')
    expect(getStateSummary()).toEqual(summary)
  })
})
