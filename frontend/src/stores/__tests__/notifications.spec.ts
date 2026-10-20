import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { Notification } from '@/stores/notifications'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'
import { notificationsAPI } from '@/api/notifications'
import { logService } from '@/services/logService'

vi.mock('@/api/notifications', () => ({
  notificationsAPI: {
    getNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(notificationsAPI)

const note = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    type: 'info',
    is_read: false,
    ...extra
  }) as unknown as Notification

describe('useNotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('computed', () => {
    it('derives unread, total unread and pending review counts', () => {
      const store = useNotificationsStore()
      store.notifications = [
        note('n1', { type: 'review_assigned' }),
        note('n2', { is_read: true }),
        note('n3', { type: 'review_assigned', is_read: true })
      ] as never

      expect(store.unreadNotifications.map(n => n.id)).toEqual(['n1'])
      expect(store.totalUnread).toBe(1)
      expect(store.pendingReviews).toBe(1)
    })
  })

  describe('fetchNotifications', () => {
    it('loads up to 50 notifications', async () => {
      const store = useNotificationsStore()
      api.getNotifications.mockResolvedValue({ notifications: [note('n1'), note('n2')] })

      await store.fetchNotifications()

      expect(api.getNotifications).toHaveBeenCalledWith({ limit: 50 })
      expect(store.notifications).toHaveLength(2)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('uses an empty list when the response has none', async () => {
      const store = useNotificationsStore()
      api.getNotifications.mockResolvedValue({} as never)

      await store.fetchNotifications()

      expect(store.notifications).toEqual([])
    })

    it('stores the API detail on failure without throwing', async () => {
      const store = useNotificationsStore()
      api.getNotifications.mockRejectedValue(
        Object.assign(new Error('x'), { response: { data: { detail: 'Forbidden' } } })
      )

      await expect(store.fetchNotifications()).resolves.toBeUndefined()

      expect(store.error).toBe('Forbidden')
      expect(store.loading).toBe(false)
      expect(logService.error).toHaveBeenCalledWith(
        'Failed to fetch notifications',
        expect.objectContaining({ error: 'x' })
      )
    })

    it('uses a generic message when the failure has no detail', async () => {
      const store = useNotificationsStore()
      api.getNotifications.mockRejectedValue(new Error('offline'))

      await store.fetchNotifications()

      expect(store.error).toBe('Failed to fetch notifications')
    })
  })

  describe('markAsRead', () => {
    it('marks the local notification read', async () => {
      const store = useNotificationsStore()
      store.notifications = [note('n1')] as never
      api.markAsRead.mockResolvedValue({} as never)

      await store.markAsRead('n1')

      expect(api.markAsRead).toHaveBeenCalledWith('n1')
      expect(store.notifications[0]?.is_read).toBe(true)
    })

    it('ignores ids that are not loaded', async () => {
      const store = useNotificationsStore()
      api.markAsRead.mockResolvedValue({} as never)

      await store.markAsRead('unknown')

      expect(store.notifications).toEqual([])
    })

    it('records the error and rethrows', async () => {
      const store = useNotificationsStore()
      api.markAsRead.mockRejectedValue(new Error('nope'))

      await expect(store.markAsRead('n1')).rejects.toThrow('nope')
      expect(store.error).toBe('Failed to mark notification as read')
    })

    it('prefers the API detail when present', async () => {
      const store = useNotificationsStore()
      api.markAsRead.mockRejectedValue(
        Object.assign(new Error('x'), { response: { data: { detail: 'Gone' } } })
      )

      await expect(store.markAsRead('n1')).rejects.toThrow('x')
      expect(store.error).toBe('Gone')
    })
  })

  describe('markAllAsRead', () => {
    it('marks every local notification read', async () => {
      const store = useNotificationsStore()
      store.notifications = [note('n1'), note('n2', { is_read: true })] as never
      api.markAllAsRead.mockResolvedValue({} as never)

      await store.markAllAsRead()

      expect(store.unreadNotifications).toEqual([])
      expect(logService.info).toHaveBeenCalledWith('Marked all notifications as read', { count: 2 })
    })

    it('records the error and rethrows', async () => {
      const store = useNotificationsStore()
      api.markAllAsRead.mockRejectedValue(new Error('down'))

      await expect(store.markAllAsRead()).rejects.toThrow('down')
      expect(store.error).toBe('Failed to mark all notifications as read')
    })

    it('prefers the API detail when present', async () => {
      const store = useNotificationsStore()
      api.markAllAsRead.mockRejectedValue(
        Object.assign(new Error('x'), { response: { data: { detail: 'Locked' } } })
      )

      await expect(store.markAllAsRead()).rejects.toThrow('x')
      expect(store.error).toBe('Locked')
    })
  })

  describe('add / remove / clear', () => {
    it('addNotification prepends, removeNotification splices, clearAll empties', () => {
      const store = useNotificationsStore()
      store.addNotification(note('n1'))
      store.addNotification(note('n2'))
      expect(store.notifications.map(n => n.id)).toEqual(['n2', 'n1'])

      store.removeNotification('n2')
      expect(store.notifications.map(n => n.id)).toEqual(['n1'])

      store.removeNotification('missing')
      expect(store.notifications).toHaveLength(1)

      store.error = 'x'
      store.clearAll()
      expect(store.notifications).toEqual([])
      expect(store.error).toBeNull()
    })

    it('clearError resets the error', () => {
      const store = useNotificationsStore()
      store.error = 'x'
      store.clearError()
      expect(store.error).toBeNull()
    })
  })

  describe('polling', () => {
    it('fetches immediately and then every 60 seconds until stopped', async () => {
      vi.useFakeTimers()
      const store = useNotificationsStore()
      api.getNotifications.mockResolvedValue({ notifications: [] })

      store.startPolling()
      expect(api.getNotifications).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(60000)
      expect(api.getNotifications).toHaveBeenCalledTimes(2)

      store.stopPolling()
      await vi.advanceTimersByTimeAsync(120000)
      expect(api.getNotifications).toHaveBeenCalledTimes(2)
      expect(logService.debug).toHaveBeenCalledWith('Notification polling stopped')
    })

    it('restarts cleanly when polling is started twice', () => {
      vi.useFakeTimers()
      const store = useNotificationsStore()
      api.getNotifications.mockResolvedValue({ notifications: [] })

      store.startPolling()
      store.startPolling()
      store.stopPolling()

      expect(logService.debug).toHaveBeenCalledWith('Notification polling started', {
        intervalMs: 60000
      })
    })

    it('stopPolling is a no-op when not polling', () => {
      const store = useNotificationsStore()
      store.stopPolling()
      expect(logService.debug).not.toHaveBeenCalledWith('Notification polling stopped')
    })
  })

  describe('toasts', () => {
    it('adds toasts with incrementing ids and auto-dismisses them', () => {
      vi.useFakeTimers()
      const store = useNotificationsStore()

      const first = store.addToast('Saved', 'success', 1000)
      const second = store.addToast('Oops', 'error', 0)

      expect(second).toBe(first + 1)
      expect(store.toasts[0]).toMatchObject({ message: 'Saved', type: 'success', visible: true })

      vi.advanceTimersByTime(1000)
      expect(store.toasts.map(t => t.id)).toEqual([second])
    })

    it('defaults to an info toast with a 5 second timeout', () => {
      vi.useFakeTimers()
      const store = useNotificationsStore()

      store.addToast('Hello')
      expect(store.toasts[0]).toMatchObject({ type: 'info', timeout: 5000 })

      vi.advanceTimersByTime(5000)
      expect(store.toasts).toEqual([])
    })

    it('removeToast removes a single toast and ignores unknown ids', () => {
      const store = useNotificationsStore()
      const id = store.addToast('a', 'info', 0)
      store.addToast('b', 'info', 0)

      store.removeToast(id)
      store.removeToast(9999)

      expect(store.toasts.map(t => t.message)).toEqual(['b'])
    })

    it('clearToasts empties the list', () => {
      const store = useNotificationsStore()
      store.addToast('a', 'info', 0)

      store.clearToasts()

      expect(store.toasts).toEqual([])
    })
  })
})
