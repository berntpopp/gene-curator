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
        <SearchButton />
        <ThemeToggle />
        <UserMenu v-if="authReady" />
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
  /**
   * Desktop side rail (md and up). Entries come from useNavEntries (route meta).
   * Below md (or signed out) App.vue renders AppBar and BottomTabs instead.
   */
  import { useRouter } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import { useScopesStore } from '@/stores/scopes'
  import BaseNavigationItem from './BaseNavigationItem.vue'
  import SearchButton from './SearchButton.vue'
  import ThemeToggle from './ThemeToggle.vue'
  import UserMenu from './UserMenu.vue'
  import { useNavEntries } from './useNavEntries'

  const router = useRouter()
  const scopesStore = useScopesStore()
  const { scopes, currentScope } = storeToRefs(scopesStore)
  const { primary, admin, isAuthenticated, authReady } = useNavEntries()

  function switchScope(id: string | null) {
    if (id) void router.push({ name: 'scope-dashboard', params: { scopeId: id } })
  }
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

  /* default 32px icon gap truncates "My work" beside its badge */
  .side-rail :deep(.v-list-item__spacer) {
    width: 16px;
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
    justify-content: space-around;
    padding: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.12);
  }
</style>
