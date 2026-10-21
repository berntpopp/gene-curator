import type { Router } from 'vue-router'
import type { useAuthStore } from '@/stores/auth'

interface NavMeta {
  label?: string
  order?: number
  requiresAuth?: boolean
  requiresGuest?: boolean
  requiredRoles?: string[]
  showInMainMenu?: boolean
  showInDropdown?: string
}

/**
 * Rail entries (route meta, same filter and role gating as SideRail).
 * ponytail: copied from SideRail.vue; swap for components/navigation/useNavEntries.ts once #351 merges.
 */
export function navEntries(router: Router, auth: ReturnType<typeof useAuthStore>, text = '') {
  const allowed = (m: NavMeta) =>
    !(m.requiresAuth && !auth.isAuthenticated) &&
    !(m.requiresGuest && auth.isAuthenticated) &&
    (!m.requiredRoles || auth.hasAnyRole(m.requiredRoles))
  return router
    .getRoutes()
    .map(r => ({ name: r.name, meta: r.meta as NavMeta }))
    .filter(
      ({ meta }) =>
        (meta.showInMainMenu || meta.showInDropdown === 'curationSetup') &&
        meta.label &&
        allowed(meta) &&
        meta.label.toLowerCase().includes(text.toLowerCase())
    )
    .sort((a, b) => (a.meta.order ?? 999) - (b.meta.order ?? 999))
}
