<template>
  <v-container fluid>
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">My Work</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">Genes assigned to you</p>
      </div>
      <v-spacer />
      <v-btn variant="outlined" class="mr-2" to="/review-queue">Review queue</v-btn>
      <v-btn color="primary" variant="flat" to="/scopes">
        <v-icon start>mdi-plus</v-icon>
        New assignment
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-6">
      {{ error }}
      <template #append>
        <v-btn class="retry" variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>

    <v-card v-else :loading="loading">
      <v-table v-if="items.length">
        <thead>
          <tr>
            <th>Gene</th>
            <th>Scope</th>
            <th>Priority</th>
            <th>Assigned</th>
            <th>Active work</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>
              <router-link
                :to="`/assignments/${item.id}`"
                class="text-primary text-decoration-none font-weight-medium"
              >
                {{ item.gene_symbol }}
              </router-link>
            </td>
            <td>
              <router-link :to="`/scopes/${item.scope_id}`" class="text-decoration-none">
                {{ scopeLabel(item) }}
              </router-link>
            </td>
            <td class="text-capitalize">{{ item.priority }}</td>
            <td>{{ formatDate(item.assigned_at) }}</td>
            <td>{{ item.has_active_work ? 'Yes' : 'No' }}</td>
          </tr>
        </tbody>
      </v-table>
      <v-card-text v-else-if="!loading" class="text-center py-8 text-medium-emphasis">
        No assignments yet. Reviewers can open the
        <router-link to="/review-queue">review queue</router-link>.
      </v-card-text>
    </v-card>

    <template v-if="canSeeAll">
      <h2 class="text-h5 font-weight-bold mt-8 mb-4">All assignments</h2>
      <GeneAssignmentManager />
    </template>
  </v-container>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { formatDate } from '@/utils/format'
  import GeneAssignmentManager from '@/components/dynamic/GeneAssignmentManager.vue'
  import { useAssignmentsStore, useAuthStore, useScopesStore } from '@/stores'
  import type { Schema } from '@/types/api'

  const assignmentsStore = useAssignmentsStore()
  const authStore = useAuthStore()
  const scopesStore = useScopesStore()

  const items = ref<Schema<'GeneScopeAssignmentSummary'>[]>([])
  const loading = ref(true)
  const error = ref<string | null>(null)
  const canSeeAll = computed(
    () => authStore.isAdmin || scopesStore.userScopes.some(s => s.user_role === 'admin')
  )

  const scopeLabel = (item: { scope_id: string; scope_name: string }) =>
    scopesStore.scopes.find(s => s.id === item.scope_id)?.display_name ?? item.scope_name

  async function load() {
    loading.value = true
    error.value = null
    try {
      const me = authStore.user?.id
      if (me) items.value = await assignmentsStore.fetchCuratorAssignments(me)
    } catch {
      error.value = 'Failed to load your assignments'
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void scopesStore.fetchUserScopes().catch(() => undefined)
    void load()
  })
</script>
