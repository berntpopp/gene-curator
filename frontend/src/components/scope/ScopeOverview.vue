<!--
  Scope Overview Component

  Displays scope information and statistics in the scope dashboard.
-->

<template>
  <div>
    <!-- Scope Information -->
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Scope information</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-identifier</v-icon>
                </template>
                <v-list-item-title>Name</v-list-item-title>
                <v-list-item-subtitle>{{ scope.name }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-format-title</v-icon>
                </template>
                <v-list-item-title>Display Name</v-list-item-title>
                <v-list-item-subtitle>{{ scope.display_name }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="scope.description">
                <template #prepend>
                  <v-icon>mdi-text</v-icon>
                </template>
                <v-list-item-title>Description</v-list-item-title>
                <v-list-item-subtitle>{{ scope.description }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="scope.institution">
                <template #prepend>
                  <v-icon>mdi-hospital-building</v-icon>
                </template>
                <v-list-item-title>Institution</v-list-item-title>
                <v-list-item-subtitle>{{ scope.institution }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon>{{ scope.is_public ? 'mdi-earth' : 'mdi-lock' }}</v-icon>
                </template>
                <v-list-item-title>Visibility</v-list-item-title>
                <v-list-item-subtitle>
                  {{ scope.is_public ? 'Public' : 'Private' }}
                </v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon :color="scope.is_active ? 'success' : 'error'">
                    {{ scope.is_active ? 'mdi-check-circle' : 'mdi-pause-circle' }}
                  </v-icon>
                </template>
                <v-list-item-title>Status</v-list-item-title>
                <v-list-item-subtitle>
                  {{ scope.is_active ? 'Active' : 'Inactive' }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Recent Activity -->
    <v-row v-if="statistics" class="mt-4">
      <v-col cols="12">
        <v-card>
          <v-card-title>Recent Activity (Last 30 Days)</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <div class="text-title-large">{{ statistics.curations_last_30_days || 0 }}</div>
                <div class="text-body-small">Curations Created</div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-title-large">{{ statistics.activations_last_30_days || 0 }}</div>
                <div class="text-body-small">Curations Activated</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
  /** Scope fields shown in the information card */
  interface ScopeInfo {
    name: string
    display_name: string
    description?: string | null
    institution?: string | null
    is_public: boolean
    is_active: boolean
  }

  /** Activity counters (the dashboard tiles show the totals) */
  interface ScopeStatisticsView {
    curations_last_30_days?: number
    activations_last_30_days?: number
  }

  defineProps<{
    scope: ScopeInfo
    statistics?: ScopeStatisticsView | null
  }>()
</script>

<style scoped>
  .v-list-item {
    margin-bottom: 8px;
  }
</style>
