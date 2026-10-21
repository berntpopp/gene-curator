import { computed } from 'vue'
import { useRouter, type RouteRecordNormalized } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useWorkBadges } from './useWorkBadges'

interface RailMeta {
  icon?: string
  label?: string
  tabLabel?: string
  tabOrder?: number
  order?: number
  requiresAuth?: boolean
  requiresGuest?: boolean
  requiredRoles?: string[]
  showInMainMenu?: boolean
  showInDropdown?: string
}

/** Route name -> badge count */
const BADGE: Record<string, (c: { needsYou: number; review: number }) => number> = {
  MyWork: c => c.needsYou,
  'review-queue': c => c.review
}

/**
 * Route-driven nav entries shared by the side rail, phone bottom tabs and command palette:
 * `showInMainMenu` for primary destinations, `showInDropdown: 'curationSetup'` for admin.
 * Also holds the shared badge poller (one request per interval however many consumers).
 */
export function useNavEntries() {
  const router = useRouter()
  const authStore = useAuthStore()
  const { isAuthenticated } = storeToRefs(authStore)
  const counts = useWorkBadges()
  // While a stored token is still being verified, show neither guest nor user entries
  const authReady = computed(() => !authStore.token || !!authStore.user)

  const allowed = (m: RailMeta) =>
    authReady.value &&
    !(m.requiresAuth && !isAuthenticated.value) &&
    !(m.requiresGuest && isAuthenticated.value) &&
    (!m.requiredRoles || authStore.hasAnyRole(m.requiredRoles))

  const entries = (pick: (m: RailMeta) => boolean) =>
    router
      .getRoutes()
      .filter(r => pick(r.meta as RailMeta) && allowed(r.meta as RailMeta))
      .sort((a, b) => ((a.meta as RailMeta).order ?? 999) - ((b.meta as RailMeta).order ?? 999))
      .map((r: RouteRecordNormalized) => ({
        name: r.name,
        to: { name: r.name },
        icon: (r.meta as RailMeta).icon,
        label: (r.meta as RailMeta).label ?? '',
        tabOrder: (r.meta as RailMeta).tabOrder ?? (r.meta as RailMeta).order ?? 999,
        tabLabel: (r.meta as RailMeta).tabLabel ?? (r.meta as RailMeta).label ?? '',
        badge: (BADGE[r.name as string]?.(counts) ?? 0) || null
      }))

  const primary = computed(() => entries(m => m.showInMainMenu === true))
  const admin = computed(() => entries(m => m.showInDropdown === 'curationSetup'))

  return { primary, admin, isAuthenticated, authReady }
}
