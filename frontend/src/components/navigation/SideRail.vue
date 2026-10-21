<template>
  <v-navigation-drawer
    permanent
    :width="200"
    class="side-rail"
    aria-label="Primary"
    :border="false"
  >
    <router-link to="/" aria-label="Gene Curator home" class="rail-brand">
      <v-img src="/img/logo.png" alt="" width="32" max-width="32" max-height="32" contain />
      <span class="text-title-medium">Gene Curator</span>
    </router-link>

    <v-select
      v-if="isAuthenticated"
      :model-value="currentScope?.id ?? null"
      :items="scopes"
      item-title="name"
      item-value="id"
      label="Scope"
      aria-label="Scope"
      density="compact"
      variant="outlined"
      hide-details
      class="rail-scope"
      @update:model-value="switchScope"
    />

    <v-list nav density="compact" class="rail-list">
      <BaseNavigationItem
        v-for="item in primary"
        :key="item.name"
        :to="item.to"
        :icon="item.icon"
        :label="item.label"
        :aria-label="item.badge ? `${item.label}, ${item.badge} pending` : item.label"
        :badge="item.badge"
        badge-color="warning"
      />
      <template v-if="admin.length > 0">
        <v-list-subheader>Admin</v-list-subheader>
        <BaseNavigationItem
          v-for="item in admin"
          :key="item.name"
          :to="item.to"
          :icon="item.icon"
          :label="item.label"
        />
      </template>
    </v-list>

    <template #append>
      <div class="rail-foot">
        <ThemeToggle />
        <UserMenu v-if="authReady" />
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
  /**
   * Desktop side rail (md and up). Entries come from route meta: `showInMainMenu` for
   * primary destinations, `showInDropdown: 'curationSetup'` for the admin group.
   * Below md App.vue renders AppBar instead.
   */
  import { computed, watch } from 'vue'
  import { useRouter, type RouteRecordNormalized } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import { useAuthStore } from '@/stores/auth'
  import { useScopesStore } from '@/stores/scopes'
  import BaseNavigationItem from './BaseNavigationItem.vue'
  import ThemeToggle from './ThemeToggle.vue'
  import UserMenu from './UserMenu.vue'
  import { useReviewBadge } from './useReviewBadge'

  interface RailMeta {
    icon?: string
    label?: string
    order?: number
    requiresAuth?: boolean
    requiresGuest?: boolean
    requiredRoles?: string[]
    showInMainMenu?: boolean
    showInDropdown?: string
  }

  const router = useRouter()
  const authStore = useAuthStore()
  const { isAuthenticated } = storeToRefs(authStore)
  const scopesStore = useScopesStore()
  const { scopes, currentScope } = storeToRefs(scopesStore)
  const pendingReviewCount = useReviewBadge()
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
        badge:
          r.name === 'review-queue' && pendingReviewCount.value > 0
            ? pendingReviewCount.value
            : null
      }))

  const primary = computed(() => entries(m => m.showInMainMenu === true))
  const admin = computed(() => entries(m => m.showInDropdown === 'curationSetup'))

  function switchScope(id: string | null) {
    if (id) void router.push({ name: 'scope-dashboard', params: { scopeId: id } })
  }

  // The rail stays mounted through login, so load when the user becomes authenticated
  watch(
    isAuthenticated,
    v => {
      if (v && scopes.value.length === 0) {
        void scopesStore.fetchUserScopes().catch(() => undefined) // switcher stays empty; page-level errors surface elsewhere
      }
    },
    { immediate: true }
  )
</script>

<style scoped>
  /* Rail navy is not a theme token (#121833); same in light and dark per design README */
  .side-rail {
    --rail-bg: #121833;
    background: var(--rail-bg) !important;
    color: #e6e8ee;
  }

  .side-rail :deep(.v-list-item),
  .side-rail :deep(.v-list-subheader),
  .side-rail :deep(.v-btn--variant-text),
  .side-rail :deep(.v-field) {
    color: #e6e8ee;
  }

  .side-rail :deep(.v-list-item--active) {
    background: rgba(255, 255, 255, 0.1);
    box-shadow: inset 3px 0 0 #5cc4cc;
  }

  .side-rail :deep(.v-list-subheader) {
    opacity: 0.7;
  }

  .rail-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 12px;
    color: inherit;
    text-decoration: none;
  }

  .rail-scope {
    margin: 0 8px 8px;
  }

  .rail-list {
    background: transparent;
  }

  .rail-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
  }
</style>
