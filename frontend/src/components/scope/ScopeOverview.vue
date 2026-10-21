<!--
  Scope Overview Component

  Displays scope information and statistics in the scope dashboard.
-->

<template>
  <div>
    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Scope information</v-card-title>
          <v-card-text>
            <dl class="scope-facts">
              <dt>Methodology</dt>
              <dd>{{ methodology || EMPTY }}</dd>
              <dt>Scope admins</dt>
              <dd>{{ admins?.length ? admins.join(', ') : EMPTY }}</dd>
              <template v-if="scope.institution">
                <dt>Institution</dt>
                <dd>{{ scope.institution }}</dd>
              </template>
            </dl>
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
  import { EMPTY } from '@/utils/format'

  /** Scope fields shown in the information card */
  interface ScopeInfo {
    institution?: string | null
  }

  /** Activity counters (the dashboard tiles show the totals) */
  interface ScopeStatisticsView {
    curations_last_30_days?: number
    activations_last_30_days?: number
  }

  defineProps<{
    scope: ScopeInfo
    statistics?: ScopeStatisticsView | null
    /** Name of the scope's workflow pair. */
    methodology?: string | null
    /** Names of the scope admins. */
    admins?: string[]
  }>()
</script>

<style scoped>
  .scope-facts {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 8px 24px;
  }

  .scope-facts dt {
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .scope-facts dd {
    margin: 0;
  }
</style>
