<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Dashboard</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Welcome back, {{ authStore.user?.name || 'User' }}
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" to="/scope-selection" size="large">
        <v-icon start>mdi-plus</v-icon>
        Start New Curation
      </v-btn>
    </div>

    <v-row>
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-domain</v-icon>
            My Clinical Scopes
            <v-spacer />
            <v-btn variant="text" size="small" to="/scopes"> View All </v-btn>
          </v-card-title>
          <v-card-text>
            <div v-if="loading" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" />
            </div>
            <div v-else-if="userScopes.length">
              <v-chip
                v-for="scope in userScopes"
                :key="scope.id"
                :color="scope.is_active ? 'success' : 'grey'"
                :to="`/scopes/${scope.id}`"
                class="ma-1"
                variant="outlined"
              >
                {{ scope.display_name || scope.name }}
              </v-chip>
            </div>
            <div v-else class="text-center py-8 text-medium-emphasis">
              <v-icon size="64" class="mb-4">mdi-domain</v-icon>
              <div class="text-body-1">No scopes assigned</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="4">
        <!-- Pending Invitations -->
        <PendingInvitations class="mb-4" />

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
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { useLogger } from '@/composables/useLogger'
  import PendingInvitations from '@/components/dashboard/PendingInvitations.vue'
  import { ref, computed, onMounted } from 'vue'
  import { useAuthStore, useScopesStore } from '@/stores'

  const logger = useLogger()
  const authStore = useAuthStore()
  const scopesStore = useScopesStore()

  const loading = ref(false)
  const userScopes = computed(() => scopesStore.userScopes)
  const isAdmin = computed(() => authStore.isAdmin)

  onMounted(async () => {
    loading.value = true
    try {
      await scopesStore.fetchUserScopes()
    } catch (error) {
      const err = error as Error
      logger.error('Failed to load dashboard data:', { error: err.message, stack: err.stack })
    } finally {
      loading.value = false
    }
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
