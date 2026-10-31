<template>
  <v-row>
    <v-col cols="12">
      <v-card variant="outlined">
        <v-card-title> Metadata </v-card-title>
        <v-card-text>
          <v-row>
            <v-col v-for="item in items" :key="item.label" cols="12" md="3">
              <div class="text-body-small text-medium-emphasis">{{ item.label }}</div>
              <div class="text-body-large">{{ item.value }}</div>
            </v-col>
          </v-row>
          <CurationHistory :curation-id="curationId" class="mt-4" />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
  /** Curation timestamps, stage and version, and its history (split from CurationDetailView). */
  import { computed } from 'vue'
  import { formatDateTime } from '@/utils/format'
  import CurationHistory from './CurationHistory.vue'

  const props = defineProps<{
    curation: {
      created_at?: string | null
      updated_at?: string | null
      workflow_stage?: string | null
      lock_version?: number | null
    }
    curationId: string
  }>()

  const items = computed(() => [
    { label: 'Created At', value: formatDateTime(props.curation.created_at) },
    { label: 'Updated At', value: formatDateTime(props.curation.updated_at) },
    { label: 'Workflow Stage', value: props.curation.workflow_stage },
    { label: 'Version', value: props.curation.lock_version }
  ])
</script>
