import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showInfo } from '@/composables/useNotifications'
import { useLogger } from '@/composables/useLogger'

/** One sign-out flow for the desktop user menu and the phone account menu. */
export function useLogout() {
  const router = useRouter()
  const authStore = useAuthStore()
  const logger = useLogger()

  return async function logout() {
    try {
      await authStore.logout()
      showInfo('Signed out')
      void router.push({ name: 'Home' })
      logger.info('User logged out')
    } catch (error) {
      const err = error instanceof Error ? error : undefined
      logger.error('Logout error:', { error: err?.message, stack: err?.stack })
    }
  }
}
