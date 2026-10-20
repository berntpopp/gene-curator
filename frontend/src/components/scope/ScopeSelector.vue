<!--
  Scope Selector Component

  **Refactored Component** - Uses new composables and service layer pattern

  **DRY Improvements**:
  - Uses useScopeUtils composable (reuses visibility icon logic)
  - Uses refactored useScopesStore with service layer

  **SOLID-SRP**:
  - Component: UI rendering and user interactions only
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **UI/UX Features**:
  - Dropdown menu for scope selection
  - Shows the institution of each scope
  - Public/private scope indicators
  - Active scope highlighting
  - Quick scope creation button

  @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-31-scope-selector-component
-->

<template>
  <v-menu offset-y>
    <template #activator="{ props }">
      <v-btn v-bind="props" color="primary" variant="outlined" prepend-icon="mdi-folder-outline">
        {{ currentScope?.display_name || 'Select Scope' }}
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-list>
      <!-- My Scopes Section -->
      <v-list-subheader>My Scopes</v-list-subheader>

      <v-list-item
        v-for="scope in userScopes"
        :key="scope.id"
        :active="currentScope?.id === scope.id"
        @click="selectScope(scope)"
      >
        <template #prepend>
          <v-icon :icon="getScopeVisibilityIcon(scope.is_public)"></v-icon>
        </template>

        <v-list-item-title>{{ scope.display_name }}</v-list-item-title>

        <v-list-item-subtitle v-if="scope.institution">{{
          scope.institution
        }}</v-list-item-subtitle>
      </v-list-item>

      <!-- Empty state -->
      <v-list-item v-if="!userScopes.length && !loading">
        <v-list-item-title class="text-medium-emphasis"> No scopes available </v-list-item-title>
      </v-list-item>

      <!-- Loading state -->
      <v-list-item v-if="loading">
        <v-list-item-title>
          <v-progress-circular indeterminate size="20" width="2" />
          Loading scopes...
        </v-list-item-title>
      </v-list-item>

      <!-- Divider and Create Scope Action -->
      <v-divider />

      <v-list-item prepend-icon="mdi-plus-circle" @click="createScope">
        <v-list-item-title>Create New Scope</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
  import { computed, onMounted } from 'vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useRouter } from 'vue-router'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useLogger } from '@/composables/useLogger'
  import type { Schema } from '@/types/api'

  /** Scoped logger from useLogger(); its JSDoc types the return as Object, so it is narrowed here */
  type LogFn = (message: string, data?: Record<string, unknown>) => void
  type ComponentLogger = { debug: LogFn; info: LogFn; error: LogFn }

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  type UserScope = Schema<'ScopeListItem'>

  /** Narrowed view of useScopeUtils() (its JSDoc types the return as Object) */
  interface ScopeUtils {
    getScopeVisibilityIcon: (isPublic: boolean) => string
  }

  const scopeStore = useScopesStore()
  const router = useRouter()
  const { getScopeVisibilityIcon } = useScopeUtils() as ScopeUtils
  const logger = useLogger() as ComponentLogger

  // ============================================
  // COMPUTED PROPERTIES
  // ============================================

  const currentScope = computed(() => scopeStore.currentScope)
  const userScopes = computed(() => scopeStore.userScopes)
  const loading = computed(() => scopeStore.loading)

  // ============================================
  // METHODS
  // ============================================

  /**
   * Select a scope and navigate to its dashboard
   * @param {Object} scope - Selected scope object
   */
  const selectScope = (scope: UserScope) => {
    logger.info('Scope selected', {
      scope_id: scope.id,
      scope_name: scope.name
    })

    scopeStore.setCurrentScope(scope)

    router.push({
      name: 'scope-dashboard',
      params: { scopeId: scope.id }
    })
  }

  /**
   * Navigate to scope creation page
   */
  const createScope = () => {
    logger.info('Creating new scope')
    router.push({ name: 'scope-create' })
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    try {
      logger.debug('Fetching user scopes')
      await scopeStore.fetchUserScopes()
    } catch (error) {
      const err = error instanceof Error ? error : undefined
      logger.error('Failed to load scopes', {
        error: err?.message,
        stack: err?.stack
      })
    }
  })
</script>

<style scoped>
  /* Ensure dropdown menu has proper z-index */
  .v-menu {
    z-index: 1000;
  }
</style>
