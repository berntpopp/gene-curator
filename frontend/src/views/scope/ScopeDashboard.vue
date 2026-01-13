<!--
  Scope Dashboard View

  **New View** - Built with DRY/SOLID principles

  **DRY Improvements**:
  - Uses useRoleColors composable (role colors)
  - Uses useScopeUtils composable (date formatting, progress calculation)
  - Uses useScopePermissions composable (permission checking)

  **SOLID-SRP**:
  - View: Orchestrates child components
  - Store: State management
  - Service: Network calls
  - Composables: Reusable utility functions

  **Features**:
  - Tab-based navigation (Overview, Members, Settings)
  - Scope statistics and progress
  - Member management (admin only)
  - Scope settings (admin only)
  - Gene list for the scope
  - Curation progress tracking

  @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-41-scope-dashboard-view
-->

<template>
  <v-container fluid>
    <!-- Loading state -->
    <v-progress-linear v-if="loading" indeterminate />

    <!-- Error state -->
    <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>

    <!-- Dashboard content -->
    <div v-else-if="scope">
      <!-- Header -->
      <v-row class="mb-4">
        <v-col>
          <div class="d-flex align-center">
            <v-icon
              :icon="getScopeVisibilityIcon(scope.is_public)"
              size="large"
              class="mr-3"
            ></v-icon>

            <div>
              <h1 class="text-h4 mb-1">{{ scope.display_name }}</h1>
              <div class="text-subtitle-1 text-medium-emphasis">
                {{ scope.description }}
              </div>
            </div>

            <v-spacer />

            <!-- User role badge -->
            <v-chip
              :color="getRoleColor(userRole)"
              :prepend-icon="getRoleIcon(userRole)"
              size="large"
            >
              {{ userRole || 'No role' }}
            </v-chip>
          </div>
        </v-col>
      </v-row>

      <!-- Stats Cards -->
      <v-row class="mb-4">
        <v-col cols="12" sm="6" md="3">
          <v-card>
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-dna" color="primary" class="mr-2"></v-icon>
                <div class="text-overline">Total Genes</div>
              </div>
              <div class="text-h4">{{ scopeStats?.total_genes || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card>
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-check-circle" color="success" class="mr-2"></v-icon>
                <div class="text-overline">Completed</div>
              </div>
              <div class="text-h4">{{ scopeStats?.completed_genes || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card>
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-progress-clock" color="warning" class="mr-2"></v-icon>
                <div class="text-overline">In Progress</div>
              </div>
              <div class="text-h4">{{ scopeStats?.in_progress_genes || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card>
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-account-group" color="info" class="mr-2"></v-icon>
                <div class="text-overline">Members</div>
              </div>
              <div class="text-h4">{{ scopeStats?.member_count || 0 }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Progress Bar -->
      <v-row class="mb-4">
        <v-col>
          <v-card>
            <v-card-text>
              <div class="text-subtitle-1 mb-2">Curation Progress</div>
              <v-progress-linear
                :model-value="curationProgress"
                color="success"
                height="20"
                striped
              >
                <strong>{{ curationProgress }}%</strong>
              </v-progress-linear>
              <div class="text-caption text-medium-emphasis mt-2">
                {{ scopeStats?.completed_genes || 0 }} of {{ scopeStats?.total_genes || 0 }} genes
                curated
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Tabs -->
      <v-card>
        <v-tabs v-model="activeTab" bg-color="primary">
          <v-tab value="overview">
            <v-icon start>mdi-view-dashboard</v-icon>
            Overview
          </v-tab>

          <v-tab value="genes">
            <v-icon start>mdi-dna</v-icon>
            Genes
          </v-tab>

          <v-tab value="curations">
            <v-icon start>mdi-file-document-multiple</v-icon>
            Curations
          </v-tab>

          <v-tab v-if="canViewMembers" value="members">
            <v-icon start>mdi-account-group</v-icon>
            Members
          </v-tab>

          <v-tab v-if="canManageScope" value="settings">
            <v-icon start>mdi-cog</v-icon>
            Settings
          </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Overview Tab -->
          <v-window-item value="overview">
            <v-card-text>
              <ScopeOverview v-if="scope" :scope="scope" :statistics="scopeStats" />
            </v-card-text>
          </v-window-item>

          <!-- Genes Tab -->
          <v-window-item value="genes">
            <v-card-text>
              <GeneList v-if="scope" :scope-id="scopeId" />
            </v-card-text>
          </v-window-item>

          <!-- Curations Tab -->
          <v-window-item value="curations">
            <v-card-text>
              <CurationList v-if="scope" :scope-id="scopeId" />
            </v-card-text>
          </v-window-item>

          <!-- Members Tab -->
          <v-window-item v-if="canViewMembers" value="members">
            <v-card-text>
              <MemberManagement v-if="scope" :scope-id="scope.id" />
            </v-card-text>
          </v-window-item>

          <!-- Settings Tab -->
          <v-window-item v-if="canManageScope" value="settings">
            <v-card-text>
              <ScopeSettings
                v-if="scope"
                :scope="scope"
                :statistics="scopeStats"
                @deleted="handleScopeDeleted"
              />
            </v-card-text>
          </v-window-item>
        </v-window>
      </v-card>
    </div>

    <!-- Scope not found -->
    <v-alert v-else type="warning" variant="tonal" class="mb-4">
      Scope not found or you don't have access.
    </v-alert>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import MemberManagement from '@/components/scope/MemberManagement.vue'

  // Lazy load heavy components (optimize initial bundle size)
  const ScopeOverview = defineAsyncComponent(() => import('@/components/scope/ScopeOverview.vue'))
  const GeneList = defineAsyncComponent(() => import('@/components/gene/GeneList.vue'))
  const CurationList = defineAsyncComponent(() => import('@/components/curation/CurationList.vue'))
  const ScopeSettings = defineAsyncComponent(() => import('@/components/scope/ScopeSettings.vue'))

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const route = useRoute()
  const router = useRouter()
  const scopeStore = useScopesStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const { getScopeVisibilityIcon, calculateProgress } = useScopeUtils()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const activeTab = ref('overview')
  const scopeStats = ref(null)

  // ============================================
  // COMPUTED PROPERTIES
  // ============================================

  const scopeId = computed(() => route.params.scopeId)
  const scope = computed(() => scopeStore.currentScope)
  const userRole = computed(() => scopeStore.currentUserRole)
  const loading = computed(() => scopeStore.loading)
  const error = computed(() => scopeStore.error)

  // Composable for permissions
  const { canManageScope, canViewMembers } = useScopePermissions(userRole)

  const curationProgress = computed(() => {
    if (!scopeStats.value) return 0
    return calculateProgress(scopeStats.value.completed_genes, scopeStats.value.total_genes)
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Handle scope deletion - navigate to scopes list
   */
  const handleScopeDeleted = () => {
    logger.info('Scope deleted, navigating to scopes list')
    router.push({ name: 'scopes' })
  }

  /**
   * Fetch scope data and statistics
   */
  const fetchScopeData = async () => {
    try {
      logger.debug('Fetching scope dashboard data', { scope_id: scopeId.value })

      // Fetch scope details
      await scopeStore.fetchScope(scopeId.value)

      // Fetch user's role in this scope
      await scopeStore.fetchUserRole(scopeId.value)

      // Fetch scope statistics
      scopeStats.value = await scopeStore.fetchStatistics(scopeId.value)

      logger.info('Scope dashboard loaded', {
        scope_id: scopeId.value,
        scope_name: scope.value?.name,
        user_role: userRole.value
      })
    } catch (err) {
      logger.error('Failed to fetch scope dashboard data', {
        scope_id: scopeId.value,
        error: err.message,
        stack: err.stack
      })
    }
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    await fetchScopeData()
  })
</script>

<style scoped>
  /* Tab content padding */
  .v-window-item {
    padding: 0;
  }

  /* Stats cards */
  .v-card .text-h4 {
    font-weight: 600;
    line-height: 1;
  }
</style>
