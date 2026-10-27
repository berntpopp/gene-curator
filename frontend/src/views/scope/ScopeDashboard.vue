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
          <div class="d-flex align-center flex-wrap ga-2">
            <div class="scope-head-text">
              <h1 class="scope-title text-headline-large mb-1">{{ scope.display_name }}</h1>
              <div class="scope-description text-body-large text-medium-emphasis">
                {{ scope.description }}
              </div>
            </div>

            <v-spacer />

            <!-- User role badge -->
            <v-chip
              :color="getRoleColor(userRole ?? '')"
              :prepend-icon="getRoleIcon(userRole ?? '')"
              size="large"
              variant="flat"
            >
              {{ scopeStore.currentRoleLabel || 'No role' }}
            </v-chip>
          </div>
        </v-col>
      </v-row>

      <!-- Stats Cards -->
      <v-row class="mb-4">
        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <div class="text-label-medium">Total Genes</div>
              </div>
              <div class="text-headline-large">{{ stat(scopeStats?.total_genes_assigned) }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <div class="text-label-medium">Completed</div>
              </div>
              <div class="text-headline-large">{{ stat(completedGenes) }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <div class="text-label-medium">In Progress</div>
              </div>
              <div class="text-headline-large">{{ stat(inProgressCount) }}</div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" sm="6" md="3">
          <v-card variant="outlined">
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <div class="text-label-medium">Members</div>
              </div>
              <div class="text-headline-large">{{ stat(scopeStats?.member_count) }}</div>
              <div
                v-if="scopeStats?.pending_invitations"
                class="text-body-small text-medium-emphasis"
              >
                {{ scopeStats.pending_invitations }} invited
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Progress Bar -->
      <v-row class="mb-4">
        <v-col>
          <v-card variant="outlined">
            <v-card-text>
              <div class="text-body-large mb-2">Curation Progress</div>
              <v-progress-linear
                :model-value="curationProgress"
                color="success"
                height="20"
                aria-label="Curation progress"
              >
                <strong>{{ curationProgress }}%</strong>
              </v-progress-linear>
              <div class="text-body-small text-medium-emphasis mt-2">
                {{ stat(completedGenes) }} of {{ genesLabel }} curated
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Tabs -->
      <v-card variant="outlined">
        <v-tabs v-model="activeTab" bg-color="primary" show-arrows>
          <v-tab value="overview">
            <v-icon start>mdi-view-dashboard</v-icon>
            Overview
          </v-tab>

          <v-tab v-if="!outsider" value="genes">
            <v-icon start>mdi-dna</v-icon>
            Genes
            <v-chip
              v-if="scopeStats?.total_genes_assigned"
              size="x-small"
              class="ml-2"
              color="white"
              variant="flat"
            >
              {{ scopeStats.total_genes_assigned }}
            </v-chip>
          </v-tab>

          <v-tab value="curations">
            <v-icon start>mdi-file-document-multiple</v-icon>
            Curations
            <v-chip
              v-if="scopeStats?.total_curations"
              size="x-small"
              class="ml-2"
              color="white"
              variant="flat"
            >
              {{ scopeStats.total_curations }}
            </v-chip>
          </v-tab>

          <v-tab v-if="canViewMembers" value="members">
            <v-icon start>mdi-account-group</v-icon>
            Members
            <v-chip
              v-if="scopeStats?.member_count"
              size="x-small"
              class="ml-2"
              color="white"
              variant="flat"
            >
              {{ scopeStats.member_count }}
            </v-chip>
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
              <ScopeOverview
                v-if="scope"
                :scope="scope"
                :statistics="scopeStats"
                :methodology="methodology"
                :admins="scopeAdmins"
              />
            </v-card-text>
          </v-window-item>

          <!-- Genes Tab -->
          <v-window-item v-if="!outsider" value="genes">
            <v-card-text>
              <GeneList v-if="scope" :scope-id="scopeId" @changed="refreshStatistics" />
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
              <MemberManagement v-if="scope" :scope-id="scope.id" @changed="refreshStatistics" />
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
              <ScopeLlmSettings v-if="scope" :scope-id="scope.id" class="mt-6" />
            </v-card-text>
          </v-window-item>
        </v-window>
      </v-card>
    </div>

    <!-- Scope not found -->
    <v-alert v-else type="warning" variant="tonal" class="mb-4">
      Scope not found or you don't have access.
      <template #append>
        <v-btn variant="text" :to="{ name: 'scopes' }">Back to scopes</v-btn>
      </template>
    </v-alert>
  </v-container>
</template>

<script setup lang="ts">
  import { EMPTY } from '@/utils/format'
  import { readableApiError } from '@/utils/apiErrorText'
  import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
  import { pluralize } from '@/utils/pluralize'
  import { useRoute, useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useRoleColors } from '@/composables/useRoleColors'
  import { useScopeUtils } from '@/composables/useScopeUtils'
  import { useScopePermissions } from '@/composables/useScopePermissions'
  import { useLogger } from '@/composables/useLogger'
  import { useWorkflowPairs } from '@/components/scope/useWorkflowPairs'
  import MemberManagement from '@/components/scope/MemberManagement.vue'

  interface ScopeStats {
    member_count?: number
    total_curations?: number
    total_genes_assigned?: number
    active_curations?: number
    completed_genes?: number
    pending_invitations?: number
    curations_last_30_days?: number
    activations_last_30_days?: number
    draft_curations?: number
    submitted_curations?: number
    curations_in_review?: number
  }

  // Lazy load heavy components (optimize initial bundle size)
  const ScopeOverview = defineAsyncComponent(() => import('@/components/scope/ScopeOverview.vue'))
  const GeneList = defineAsyncComponent(() => import('@/components/gene/GeneList.vue'))
  const CurationList = defineAsyncComponent(() => import('@/components/curation/CurationList.vue'))
  const ScopeSettings = defineAsyncComponent(() => import('@/components/scope/ScopeSettings.vue'))
  const ScopeLlmSettings = defineAsyncComponent(
    () => import('@/components/scope/ScopeLlmSettings.vue')
  )

  // ============================================
  // COMPOSABLES & STORE
  // ============================================

  const route = useRoute()
  const router = useRouter()
  const scopeStore = useScopesStore()
  const { getRoleColor, getRoleIcon } = useRoleColors()
  const { calculateProgress } = useScopeUtils()
  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const scopeStats = ref<ScopeStats | undefined>(undefined)
  // A logged-in non-member of a public scope: skip member-only calls and the Genes tab (#484)
  const outsider = ref(false)
  // Em dash until statistics arrive, never a fake 0
  const stat = (n: number | null | undefined) => (scopeStats.value ? (n ?? 0) : EMPTY)
  const genesLabel = computed(() =>
    scopeStats.value
      ? pluralize(scopeStats.value.total_genes_assigned ?? 0, 'gene')
      : `${EMPTY} genes`
  )

  // Overview facts: methodology name and the scope admins
  const { workflowPairs, loadWorkflowPairs } = useWorkflowPairs(() => undefined)
  const methodology = computed(
    () => workflowPairs.value.find(p => p.id === scope.value?.default_workflow_pair_id)?.displayName
  )
  const scopeAdmins = computed(() =>
    scopeStore
      .getScopeUsers(scopeId.value)
      .filter(m => m.role === 'admin')
      .map(m => m.user_full_name || m.user_username || m.user_email || '')
      .filter(Boolean)
  )

  // ============================================
  // COMPUTED PROPERTIES
  // ============================================

  const scopeId = computed(() => route.params.scopeId as string)

  // Valid tab values
  const validTabs: string[] = ['overview', 'genes', 'curations', 'members', 'settings']

  // Active tab synced with route (must be after scopeId)
  const activeTab = computed({
    get: () => {
      const tab = route.params.tab as string
      return validTabs.includes(tab) && !(outsider.value && tab === 'genes') ? tab : 'overview'
    },
    set: (tabValue: string) => {
      if (tabValue === route.params.tab) return
      router.push({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value, tab: tabValue }
      })
    }
  })
  const scope = computed(() => scopeStore.currentScope)
  const userRole = computed(() => scopeStore.currentUserRole)
  const loading = computed(() => scopeStore.loading)
  const error = computed(() => scopeStore.error)

  // Composable for permissions
  const { canManageScope, canViewMembers } = useScopePermissions(userRole)

  // In-progress count: draft + submitted + in_review curations
  const inProgressCount = computed<number>(() => {
    if (!scopeStats.value) return 0
    return (
      (scopeStats.value.draft_curations || 0) +
      (scopeStats.value.submitted_curations || 0) +
      (scopeStats.value.curations_in_review || 0)
    )
  })

  // Completed genes can never exceed the total
  const completedGenes = computed<number>(() => {
    const stats = scopeStats.value
    if (!stats) return 0
    return Math.min(
      stats.completed_genes ?? stats.active_curations ?? 0,
      stats.total_genes_assigned ?? 0
    )
  })

  const curationProgress = computed<number>(() =>
    Math.min(calculateProgress(completedGenes.value, scopeStats.value?.total_genes_assigned), 100)
  )

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

  /** Re-read the tiles after genes were added, assigned or removed. */
  const refreshStatistics = async () => {
    scopeStats.value =
      ((await scopeStore.fetchStatistics(scopeId.value)) as ScopeStats | null) ?? undefined
  }

  /**
   * Fetch scope data and statistics
   */
  const fetchScopeData = async () => {
    try {
      logger.debug('Fetching scope dashboard data', { scope_id: scopeId.value })

      // The scope detail sets the role before v-tabs first renders (#175). A non-member may
      // open a public scope: no role, so no member-only calls (#393, #484)
      await scopeStore.fetchScope(scopeId.value)
      outsider.value = !scopeStore.currentUserRole
      if (!outsider.value) await refreshStatistics().catch(() => undefined)

      // Overview facts are best effort: the page works without them
      await Promise.allSettled([
        loadWorkflowPairs(),
        outsider.value ? undefined : scopeStore.fetchMembers(scopeId.value)
      ])

      logger.info('Scope dashboard loaded', {
        scope_id: scopeId.value,
        scope_name: scope.value?.name,
        user_role: userRole.value
      })
    } catch (err) {
      scopeStore.error ||= readableApiError(err, 'Could not load the scope')
      logger.error('Failed to fetch scope dashboard data', {
        scope_id: scopeId.value,
        error: (err as Error).message,
        stack: (err as Error).stack
      })
    }
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  onMounted(async () => {
    // Redirect to default tab if none specified
    if (!route.params.tab) {
      router.replace({
        name: 'scope-dashboard',
        params: { scopeId: scopeId.value, tab: 'overview' }
      })
    }
    await fetchScopeData()
  })
</script>

<style scoped>
  /* A long unbroken word must wrap, not widen the page (phone) */
  .scope-title,
  .scope-description {
    overflow-wrap: anywhere;
  }

  .scope-head-text {
    min-width: 0;
  }

  /* Tab content padding */
  .v-window-item {
    padding: 0;
  }

  /* Stats cards */
  .v-card .text-headline-large {
    font-weight: 600;
    line-height: 1;
  }
</style>
