<!--
  Scope List View

  **New View** - Built with DRY/SOLID principles

  **DRY Improvements**:
  - Uses useRoleColors composable (role colors/icons)
  - Uses useScopeUtils composable (visibility icons, date formatting, progress calculation)
  - Uses refactored useScopesStore with service layer

  **SOLID-SRP**:
  - View: List UI and filtering
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **Features**:
  - List all scopes (public + user's private scopes)
  - Filter by public/private
  - Search by name/description
  - Sort by various criteria
  - Navigate to scope dashboard
  - Create new scope button (admin only)

  @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-43-scope-list-view
-->

<template>
  <v-container fluid>
    <v-row>
      <v-col>
        <!-- Header -->
        <div class="d-flex align-center mb-4">
          <div>
            <h1 class="text-h4 mb-1">Clinical Scopes</h1>
            <div class="text-subtitle-1 text-medium-emphasis">
              Browse and manage curation scopes
            </div>
          </div>

          <v-spacer />

          <v-btn color="primary" prepend-icon="mdi-plus" @click="navigateToCreate">
            Create Scope
          </v-btn>
        </div>

        <!-- Filters and Search -->
        <v-card class="mb-4">
          <v-card-text>
            <v-row>
              <!-- Search -->
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="searchQuery"
                  prepend-inner-icon="mdi-magnify"
                  label="Search scopes"
                  placeholder="Type to search..."
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                ></v-text-field>
              </v-col>

              <!-- Visibility Filter -->
              <v-col cols="12" sm="6" md="3">
                <v-select
                  v-model="visibilityFilter"
                  :items="visibilityOptions"
                  label="Visibility"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-select>
              </v-col>

              <!-- Status Filter -->
              <v-col cols="12" sm="6" md="3">
                <v-select
                  v-model="statusFilter"
                  :items="statusOptions"
                  label="Status"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-select>
              </v-col>

              <!-- Sort -->
              <v-col cols="12" sm="6" md="2">
                <v-select
                  v-model="sortBy"
                  :items="sortOptions"
                  label="Sort By"
                  variant="outlined"
                  density="compact"
                  hide-details
                ></v-select>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Loading state -->
        <v-progress-linear v-if="loading" indeterminate />

        <!-- Scopes Grid -->
        <v-row v-else-if="filteredScopes.length > 0">
          <v-col v-for="scope in filteredScopes" :key="scope.id" cols="12" sm="6" md="4" lg="3">
            <v-card
              hover
              class="scope-card"
              :class="{ 'inactive-scope': !scope.is_active }"
              @click="navigateToScope(scope)"
            >
              <v-card-title class="d-flex align-center">
                <v-icon
                  :icon="getScopeVisibilityIcon(scope.is_public)"
                  :color="scope.is_public ? 'primary' : 'warning'"
                  class="mr-2"
                ></v-icon>
                <span class="text-truncate">{{ scope.display_name }}</span>
              </v-card-title>

              <v-card-subtitle class="text-truncate">
                {{ scope.institution || 'No institution' }}
              </v-card-subtitle>

              <v-card-text>
                <div class="text-caption text-truncate-2 mb-3">
                  {{ scope.description || 'No description' }}
                </div>

                <!-- Statistics -->
                <div class="d-flex align-center mb-2">
                  <v-icon icon="mdi-dna" size="small" class="mr-1"></v-icon>
                  <span class="text-caption"> {{ scope.stats?.total_genes || 0 }} genes </span>
                </div>

                <div class="d-flex align-center mb-2">
                  <v-icon icon="mdi-account-group" size="small" class="mr-1"></v-icon>
                  <span class="text-caption"> {{ scope.stats?.member_count || 0 }} members </span>
                </div>

                <!-- Progress Bar -->
                <v-progress-linear
                  :model-value="calculateScopeProgress(scope)"
                  color="success"
                  height="8"
                  rounded
                  class="mb-2"
                ></v-progress-linear>

                <div class="text-caption text-medium-emphasis">
                  {{ calculateScopeProgress(scope) }}% complete
                </div>
              </v-card-text>

              <v-card-actions>
                <!-- User Role Badge -->
                <v-chip
                  v-if="scope.user_role"
                  :color="getRoleColor(scope.user_role)"
                  :prepend-icon="getRoleIcon(scope.user_role)"
                  size="small"
                >
                  {{ scope.user_role }}
                </v-chip>

                <v-spacer />

                <!-- Status Badge -->
                <v-chip
                  :color="scope.is_active ? 'success' : 'warning'"
                  size="small"
                  variant="flat"
                >
                  {{ scope.is_active ? 'Active' : 'Inactive' }}
                </v-chip>
              </v-card-actions>

              <!-- Due Date (if set) -->
              <v-card-text v-if="scope.due_date" class="pt-0">
                <v-divider class="mb-2" />
                <div class="d-flex align-center text-caption">
                  <v-icon icon="mdi-calendar" size="small" class="mr-1"></v-icon>
                  <span>Due: {{ formatDate(scope.due_date) }}</span>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Empty State -->
        <v-card v-else>
          <v-card-text class="text-center py-12">
            <v-icon icon="mdi-folder-outline" size="64" color="grey-lighten-1"></v-icon>
            <div class="text-h6 mt-4 mb-2">No scopes found</div>
            <div class="text-body-2 text-medium-emphasis mb-4">
              Try adjusting your filters or create a new scope
            </div>
            <v-btn color="primary" prepend-icon="mdi-plus" @click="navigateToCreate">
              Create Scope
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const router = useRouter()
  const scopeStore = useScopesStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const { getScopeVisibilityIcon, formatDate, calculateProgress } = useScopeUtils()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const searchQuery = ref('')
  const visibilityFilter = ref('all')
  const statusFilter = ref('all')
  const sortBy = ref('name')

  // ============================================
  // OPTIONS
  // ============================================

  const visibilityOptions = [
    { title: 'All Scopes', value: 'all' },
    { title: 'Public Only', value: 'public' },
    { title: 'Private Only', value: 'private' }
  ]

  const statusOptions = [
    { title: 'All Status', value: 'all' },
    { title: 'Active Only', value: 'active' },
    { title: 'Inactive Only', value: 'inactive' }
  ]

  const sortOptions = [
    { title: 'Name (A-Z)', value: 'name' },
    { title: 'Recently Created', value: 'created_desc' },
    { title: 'Due Date', value: 'due_date' },
    { title: 'Progress', value: 'progress' },
    { title: 'Member Count', value: 'members' }
  ]

  // ============================================
  // COMPUTED PROPERTIES
  // ============================================

  const scopes = computed(() => scopeStore.scopes)
  const loading = computed(() => scopeStore.loading)

  /**
   * Filter and sort scopes based on user selection
   */
  const filteredScopes = computed(() => {
    let result = [...scopes.value]

    // Search filter
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(
        scope =>
          scope.display_name.toLowerCase().includes(query) ||
          scope.name.toLowerCase().includes(query) ||
          scope.description?.toLowerCase().includes(query) ||
          scope.institution?.toLowerCase().includes(query)
      )
    }

    // Visibility filter
    if (visibilityFilter.value === 'public') {
      result = result.filter(scope => scope.is_public)
    } else if (visibilityFilter.value === 'private') {
      result = result.filter(scope => !scope.is_public)
    }

    // Status filter
    if (statusFilter.value === 'active') {
      result = result.filter(scope => scope.is_active)
    } else if (statusFilter.value === 'inactive') {
      result = result.filter(scope => !scope.is_active)
    }

    // Sort
    switch (sortBy.value) {
      case 'name':
        result.sort((a, b) => a.display_name.localeCompare(b.display_name))
        break
      case 'created_desc':
        result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        break
      case 'due_date':
        result.sort((a, b) => {
          if (!a.due_date) return 1
          if (!b.due_date) return -1
          return new Date(a.due_date) - new Date(b.due_date)
        })
        break
      case 'progress':
        result.sort((a, b) => calculateScopeProgress(b) - calculateScopeProgress(a))
        break
      case 'members':
        result.sort((a, b) => (b.stats?.member_count || 0) - (a.stats?.member_count || 0))
        break
    }

    return result
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Calculate progress for a scope
   */
  const calculateScopeProgress = scope => {
    if (!scope.stats) return 0
    return calculateProgress(scope.stats.completed_genes, scope.stats.total_genes)
  }

  /**
   * Navigate to scope dashboard
   */
  const navigateToScope = scope => {
    logger.info('Navigating to scope dashboard', {
      scope_id: scope.id,
      scope_name: scope.name
    })

    router.push({
      name: 'scope-dashboard',
      params: { scopeId: scope.id }
    })
  }

  /**
   * Navigate to scope creation page
   */
  const navigateToCreate = () => {
    logger.info('Navigating to scope creation')
    router.push({ name: 'scope-create' })
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    try {
      logger.debug('Fetching all scopes')
      await scopeStore.fetchUserScopes()
      logger.info('Scopes loaded', { count: scopes.value.length })
    } catch (error) {
      logger.error('Failed to fetch scopes', {
        error: error.message,
        stack: error.stack
      })
    }
  })
</script>

<style scoped>
  /* Scope card hover effect */
  .scope-card {
    cursor: pointer;
    transition:
      transform 0.2s,
      box-shadow 0.2s;
    height: 100%;
  }

  .scope-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  }

  /* Inactive scope styling */
  .inactive-scope {
    opacity: 0.7;
  }

  /* Text truncation for multiline */
  .text-truncate-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    min-height: 2.5em;
  }
</style>
