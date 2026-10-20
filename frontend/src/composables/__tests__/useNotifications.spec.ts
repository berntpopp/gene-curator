import { describe, it, expect, beforeEach } from 'vitest'
import {
  useNotifications,
  snackbarState,
  showSnackbar,
  showSuccess,
  showError,
  showWarning,
  showInfo
} from '../useNotifications'

describe('useNotifications', () => {
  beforeEach(() => {
    snackbarState.show = false
    snackbarState.message = ''
    snackbarState.color = 'info'
    snackbarState.timeout = 5000
  })

  it('showSnackbar sets message, color, timeout and shows the snackbar', () => {
    showSnackbar('Saved', 'primary', 1234)

    expect(snackbarState).toEqual({ show: true, message: 'Saved', color: 'primary', timeout: 1234 })
  })

  it('showSnackbar defaults to info colour and 5s timeout', () => {
    showSnackbar('Hello')

    expect(snackbarState.color).toBe('info')
    expect(snackbarState.timeout).toBe(5000)
  })

  it.each([
    [showSuccess, 'success', 5000],
    [showError, 'error', 8000],
    [showWarning, 'warning', 6000],
    [showInfo, 'info', 5000]
  ])('shorthand helper uses its colour and default timeout (%s)', (helper, color, timeout) => {
    helper('msg')

    expect(snackbarState.color).toBe(color)
    expect(snackbarState.timeout).toBe(timeout)
    expect(snackbarState.show).toBe(true)
  })

  it('shorthand helpers honour an explicit timeout', () => {
    showError('boom', 100)

    expect(snackbarState.timeout).toBe(100)
  })

  it('useNotifications exposes the shared state and helpers', () => {
    const api = useNotifications()

    expect(api.snackbarState).toBe(snackbarState)
    api.showWarning('careful')
    expect(snackbarState.message).toBe('careful')
    expect(snackbarState.color).toBe('warning')
  })
})
