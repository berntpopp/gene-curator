<template>
  <v-expansion-panels
    v-if="view && (view.enabled || view.runs.length)"
    v-model="open"
    data-test="llm-second-view"
  >
    <v-expansion-panel value="ai">
      <v-expansion-panel-title>
        <v-icon start icon="mdi-lightbulb-outline" />
        AI second view (advisory)
        <v-chip v-if="disagreements" size="small" color="warning" class="ml-2">
          {{ disagreements }} disagreement{{ disagreements === 1 ? '' : 's' }}
        </v-chip>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <p class="text-body-medium text-medium-emphasis mb-2">
          AI output. It never sees the curator's scores or classification, and never changes
          evidence, scores, classification or workflow state; it cannot approve.
        </p>
        <p v-for="run in view.runs" :key="run.run_id" class="text-body-small mb-1">
          {{ run.strategy }}: {{ run.model_id }}, prompt v{{ run.prompt_version ?? '?' }},
          methodology v{{ run.methodology_version ?? '?' }}
        </p>
        <div class="d-flex align-center ga-2 my-3">
          <v-btn
            v-if="view.enabled"
            :loading="busy"
            :disabled="view.pending"
            color="primary"
            variant="tonal"
            data-test="request-second-view"
            @click="request"
          >
            {{ view.runs.length ? 'Run again' : 'Run second view' }}
          </v-btn>
          <v-btn v-if="view.pending" variant="text" data-test="refresh-second-view" @click="load">
            Running in the background; refresh
          </v-btn>
        </div>
        <v-table v-if="view.runs.length" density="compact" class="mb-4">
          <thead>
            <tr>
              <th>Category</th>
              <th>Human</th>
              <th>Advocate</th>
              <th>Skeptic</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in view.diff"
              :key="row.category"
              :class="{ 'font-weight-bold': row.disagree }"
              data-test="diff-row"
            >
              <td>
                <v-icon
                  v-if="row.disagree"
                  icon="mdi-alert-circle-outline"
                  color="warning"
                  size="small"
                  aria-label="Disagreement"
                />
                {{ row.category }}
              </td>
              <td>{{ shown(row.human) }}</td>
              <td>{{ shown(row.advocate) }}</td>
              <td>{{ shown(row.skeptic) }}</td>
            </tr>
          </tbody>
        </v-table>
        <v-list v-if="view.findings.length" lines="three" density="compact">
          <v-list-item v-for="f in view.findings" :key="f.id" data-test="finding">
            <v-list-item-title>
              <v-chip size="x-small" class="mr-1">{{ f.strategy }}</v-chip>
              {{ f.category }}
            </v-list-item-title>
            <div class="text-body-medium">{{ f.message }}</div>
            <div class="text-body-small text-medium-emphasis">
              Cites: {{ f.citations.join(', ') }}
            </div>
            <template #append>
              <v-btn-toggle
                :model-value="f.decision"
                density="compact"
                variant="outlined"
                divided
                :aria-label="`Decision on ${f.category} finding`"
              >
                <v-btn value="accepted" size="small" @click="decide(f.id, 'accepted')">
                  Accept
                </v-btn>
                <v-btn value="dismissed" size="small" @click="decide(f.id, 'dismissed')">
                  Dismiss
                </v-btn>
              </v-btn-toggle>
            </template>
          </v-list-item>
        </v-list>
        <p v-else-if="view.runs.length" class="text-body-medium">No cited findings.</p>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { showError } from '@/composables/useNotifications'
  import { llmErrorMessage, useLlmStore } from '@/stores/llm'
  import type { Schema } from '@/types/api'

  const props = defineProps<{ scopeId: string; curationId: string }>()

  const store = useLlmStore()
  const view = ref<Schema<'SecondViewOut'> | null>(null)
  const open = ref<string[]>([])
  const busy = ref(false)

  const disagreements = computed(() => view.value?.diff.filter(r => r.disagree).length ?? 0)
  const shown = (v: number | string | null | undefined) => (v === null || v === undefined ? '-' : v)

  async function load(): Promise<void> {
    try {
      view.value = await store.secondView(props.scopeId, props.curationId)
    } catch {
      view.value = null // not a reviewer here, or the feature is off: show nothing
    }
  }

  async function request(): Promise<void> {
    busy.value = true
    try {
      view.value = await store.requestSecondView(props.scopeId, props.curationId)
    } catch (err) {
      showError(llmErrorMessage(err, 'Could not start the AI second view'))
    } finally {
      busy.value = false
    }
  }

  async function decide(id: string, decision: 'accepted' | 'dismissed'): Promise<void> {
    try {
      const row = await store.decideFinding(id, { decision })
      const findings = view.value?.findings ?? []
      const i = findings.findIndex(f => f.id === id)
      if (i >= 0) findings[i] = row
    } catch (err) {
      showError(llmErrorMessage(err, 'Decision not saved'))
    }
  }

  onMounted(load)
</script>
