<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Dashboard</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Welcome back, {{ currentUser?.full_name || 'User' }}
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" to="/scope-selection" size="large">
        <v-icon start>mdi-plus</v-icon>
        Start New Curation
      </v-btn>
    </div>

    <!-- Quick Stats Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="primary" class="mb-2">mdi-account-group</v-icon>
            <div class="text-h4 font-weight-bold text-primary">
              {{ stats?.active_assignments || 0 }}
            </div>
            <div class="text-body-2 text-medium-emphasis">Active Assignments</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="success" class="mb-2">mdi-check-circle</v-icon>
            <div class="text-h4 font-weight-bold text-success">
              {{ stats?.completed_curations || 0 }}
            </div>
            <div class="text-body-2 text-medium-emphasis">Completed This Month</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="warning" class="mb-2">mdi-clock-outline</v-icon>
            <div class="text-h4 font-weight-bold text-warning">
              {{ stats?.pending_reviews || 0 }}
            </div>
            <div class="text-body-2 text-medium-emphasis">Pending Review</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="info" class="mb-2">mdi-domain</v-icon>
            <div class="text-h4 font-weight-bold text-info">{{ stats?.active_scopes || 0 }}</div>
            <div class="text-body-2 text-medium-emphasis">Active Scopes</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Activity & My Assignments -->
    <v-row>
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-history</v-icon>
            Recent Activity
            <v-spacer />
            <v-btn variant="text" size="small" to="/assignments"> View All </v-btn>
          </v-card-title>

          <v-card-text>
            <div v-if="loading" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" />
            </div>

            <v-list v-else-if="recentActivity.length" density="compact">
              <v-list-item
                v-for="(activity, index) in recentActivity"
                :key="index"
                :to="getActivityLink(activity)"
              >
                <template #prepend>
                  <v-avatar :color="getActivityColor(activity.type)" size="32">
                    <v-icon size="18" color="white">{{ getActivityIcon(activity.type) }}</v-icon>
                  </v-avatar>
                </template>

                <v-list-item-title>{{ activity.title }}</v-list-item-title>
                <v-list-item-subtitle>
                  {{ activity.description }} • {{ formatDate(activity.created_at) }}
                </v-list-item-subtitle>

                <template #append>
                  <v-chip :color="getStatusColor(activity.status)" size="small" variant="outlined">
                    {{ formatStatus(activity.status) }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>

            <div v-else class="text-center py-8 text-medium-emphasis">
              <v-icon size="64" class="mb-4">mdi-history</v-icon>
              <div class="text-body-1">No recent activity</div>
              <div class="text-body-2">Start a new curation to see activity here</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="4">
        <!-- Quick Actions -->
        <v-card class="mb-4">
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-flash</v-icon>
            Quick Actions
          </v-card-title>
          <v-card-text>
            <div class="d-grid gap-2">
              <v-btn color="primary" variant="outlined" block to="/scope-selection">
                <v-icon start>mdi-plus</v-icon>
                New Curation
              </v-btn>

              <v-btn color="secondary" variant="outlined" block to="/assignments">
                <v-icon start>mdi-view-list</v-icon>
                View Assignments
              </v-btn>

              <v-btn color="info" variant="outlined" block to="/validation">
                <v-icon start>mdi-check-decagram</v-icon>
                Validation Dashboard
              </v-btn>

              <v-btn v-if="isAdmin" color="warning" variant="outlined" block to="/admin/schemas">
                <v-icon start>mdi-cog</v-icon>
                Schema Management
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- My Scopes -->
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-domain</v-icon>
            My Clinical Scopes
          </v-card-title>
          <v-card-text>
            <div v-if="userScopes.length">
              <v-chip
                v-for="scope in userScopes"
                :key="scope.id"
                :color="scope.is_active ? 'success' : 'grey'"
                class="ma-1"
                size="small"
                variant="outlined"
              >
                {{ scope.display_name }}
              </v-chip>
            </div>
            <div v-else class="text-center py-4 text-medium-emphasis">
              <v-icon size="48" class="mb-2">mdi-domain</v-icon>
              <div class="text-body-2">No scopes assigned</div>
              <v-btn
                v-if="isAdmin"
                color="primary"
                variant="text"
                size="small"
                to="/admin/users"
                class="mt-2"
              >
                Manage Scopes
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted } from 'vue'
  import { useAuthStore, useScopesStore } from '@/stores'

  const authStore = useAuthStore()
  const scopesStore = useScopesStore()

  const loading = ref(false)
  const stats = ref({
    active_assignments: 0,
    completed_curations: 0,
    pending_reviews: 0,
    active_scopes: 0
  })
  const recentActivity = ref([])
  const userScopes = ref([])

  const currentUser = computed(() => authStore.user)
  const isAdmin = computed(() => authStore.hasRole('admin'))

  const getActivityColor = type => {
    const colorMap = {
      assignment_created: 'primary',
      curation_submitted: 'success',
      review_requested: 'warning',
      workflow_advanced: 'info',
      assignment_completed: 'success'
    }
    return colorMap[type] || 'grey'
  }

  const getActivityIcon = type => {
    const iconMap = {
      assignment_created: 'mdi-plus',
      curation_submitted: 'mdi-check',
      review_requested: 'mdi-eye',
      workflow_advanced: 'mdi-arrow-right',
      assignment_completed: 'mdi-star'
    }
    return iconMap[type] || 'mdi-circle'
  }

  const getStatusColor = status => {
    const colorMap = {
      draft: 'grey',
      in_progress: 'primary',
      pending_review: 'warning',
      under_review: 'info',
      completed: 'success',
      rejected: 'error'
    }
    return colorMap[status] || 'grey'
  }

  const formatStatus = status => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = dateString => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const getActivityLink = activity => {
    switch (activity.type) {
      case 'assignment_created':
      case 'curation_submitted':
      case 'assignment_completed':
        return `/assignments/${activity.assignment_id}`
      default:
        return '/assignments'
    }
  }

  const loadDashboardData = async () => {
    loading.value = true
    try {
      // Load dashboard stats from auth store
      const dashboardStats = await authStore.fetchDashboardStats()
      if (dashboardStats) {
        stats.value = { ...stats.value, ...dashboardStats }
      }

      // Load user scopes
      const scopes = await authStore.getUserScopes()
      userScopes.value = scopes || []

      // Load scopes to get active scopes count
      try {
        await scopesStore.fetchScopes()
        stats.value.active_scopes = scopesStore.getActiveScopesCount || 0
      } catch (scopeError) {
        console.warn('Failed to load scopes:', scopeError)
        stats.value.active_scopes = 0
      }

      // Clear recent activity for now (can be implemented later)
      recentActivity.value = []
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      // Set default values on error
      stats.value = {
        active_assignments: 0,
        completed_curations: 0,
        pending_reviews: 0,
        active_scopes: 0
      }
      userScopes.value = []
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    loadDashboardData()
  })
</script>

<style scoped>
  .d-grid {
    display: grid;
  }

  .gap-2 {
    gap: 8px;
  }
</style>
