<!--
  Scope Selector Component

  **Refactored Component** - Uses new composables and service layer pattern

  **DRY Improvements**:
  - Uses useRoleColors composable (eliminates duplicate role color logic)
  - Uses useScopeUtils composable (reuses visibility icon logic)
  - Uses refactored useScopesStore with service layer

  **SOLID-SRP**:
  - Component: UI rendering and user interactions only
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **UI/UX Features**:
  - Dropdown menu for scope selection
  - Shows user's role within each scope
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

        <v-list-item-subtitle>
          <v-chip
            size="x-small"
            :color="getRoleColor(scope.user_role)"
            :prepend-icon="getRoleIcon(scope.user_role)"
          >
            {{ scope.user_role }}
          </v-chip>
        </v-list-item-subtitle>
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

<script setup>
  import { computed, onMounted } from 'vue'
  import { useScopesStore } from '@/stores/scopes'
  import { useRouter } from 'vue-router'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const scopeStore = useScopesStore()
  const router = useRouter()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const { getScopeVisibilityIcon } = useScopeUtils()
  const logger = useLogger()

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
  const selectScope = scope => {
    logger.info('Scope selected', {
      scope_id: scope.id,
      scope_name: scope.name,
      user_role: scope.user_role
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
      logger.error('Failed to load scopes', {
        error: error.message,
        stack: error.stack
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
