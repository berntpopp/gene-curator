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
      <v-btn color="primary" variant="flat" to="/scopes" size="large">
        <v-icon start>mdi-plus</v-icon>
        Start new curation
      </v-btn>
    </div>

    <v-row>
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-domain</v-icon>
            {{ TERMINOLOGY.SCOPES }}
            <v-spacer />
            <v-btn variant="text" size="small" to="/scopes"> View all </v-btn>
          </v-card-title>
          <v-card-text>
            <div v-if="loading" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" />
            </div>
            <v-alert v-else-if="scopesStore.error" type="error" variant="tonal">
              {{ scopesStore.error }}
              <template #append>
                <v-btn class="retry" variant="text" @click="loadScopes">Retry</v-btn>
              </template>
            </v-alert>
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
            Quick actions
          </v-card-title>
          <v-card-text>
            <div class="d-grid ga-2">
              <v-btn color="primary" variant="outlined" block to="/scopes">
                <v-icon start>mdi-plus</v-icon>
                New curation
              </v-btn>

              <v-btn variant="outlined" block to="/assignments">
                <v-icon start>mdi-view-list</v-icon>
                View assignments
              </v-btn>

              <v-btn v-if="isAdmin" color="warning" variant="outlined" block to="/admin/schemas">
                <v-icon start>mdi-cog</v-icon>
                {{ TERMINOLOGY.TEMPLATES }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
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

  async function loadScopes() {
    loading.value = true
    try {
      await scopesStore.fetchUserScopes()
    } catch (error) {
      const err = error as Error
      logger.error('Failed to load dashboard data:', { error: err.message, stack: err.stack })
    } finally {
      loading.value = false
    }
  }

  onMounted(loadScopes)
</script>

<style scoped>
  .d-grid {
    display: grid;
  }
</style>
