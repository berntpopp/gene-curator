<template>
  <div>
    <div class="d-flex align-center mb-2">
      <p class="text-body-small text-medium-emphasis">
        Example evidence with the expected total and class. Publishing refuses a version whose tests
        fail.
      </p>
      <v-spacer />
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-check-circle"
        :loading="running"
        :disabled="!tests?.length"
        @click="emit('run')"
      >
        Run tests
      </v-btn>
    </div>
    <v-card v-for="(test, i) in tests ?? []" :key="i" variant="outlined" class="mb-3">
      <v-card-text>
        <div class="d-flex ga-2 align-start">
          <v-text-field v-model="test.name" label="Name" density="compact" variant="outlined" />
          <v-text-field
            :model-value="test.expect.total ?? ''"
            label="Expected total"
            type="number"
            density="compact"
            variant="outlined"
            @update:model-value="v => setNumber(test.expect, 'total', v)"
          />
          <v-combobox
            :model-value="test.expect.class ?? ''"
            :items="classKeys"
            label="Expected class"
            density="compact"
            variant="outlined"
            @update:model-value="v => setText(test.expect, 'class', v)"
          />
          <v-btn
            aria-label="Remove test"
            icon="mdi-delete"
            variant="text"
            color="error"
            @click="remove(i)"
          />
        </div>
        <v-textarea
          :model-value="evidenceText(i, test.evidence_data)"
          label="Evidence (JSON, as a curation stores it)"
          rows="4"
          auto-grow
          variant="outlined"
          class="code"
          :error-messages="parseErrors[i] ? [parseErrors[i]] : []"
          @update:model-value="v => setEvidence(i, v)"
        />
        <div v-if="results[i]" class="d-flex align-center ga-2 flex-wrap" role="status">
          <v-chip
            :color="results[i].failures.length ? 'error' : 'success'"
            size="small"
            variant="flat"
            :prepend-icon="results[i].failures.length ? 'mdi-close' : 'mdi-check'"
          >
            {{ results[i].failures.length ? 'Failed' : 'Passed' }}
          </v-chip>
          <span class="text-body-small">
            total {{ results[i].total }} · class {{ results[i].verdict }}
          </span>
          <span v-for="f in results[i].failures" :key="f" class="text-body-small text-error">
            {{ f }}
          </span>
        </div>
      </v-card-text>
    </v-card>
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="add">Test</v-btn>
  </div>
</template>

<script setup lang="ts">
  import { reactive } from 'vue'
  import { setNumber, setText, type ScoringTest } from './pointModel'
  import type { TestResult } from './usePointModelChecks'

  defineProps<{ results: TestResult[]; running: boolean; classKeys: string[] }>()
  const emit = defineEmits<{ run: [] }>()
  const tests = defineModel<ScoringTest[] | undefined>()

  // Text being typed that is not JSON yet stays in the box with its error
  const drafts = reactive<Record<number, string>>({})
  const parseErrors = reactive<Record<number, string>>({})

  const evidenceText = (i: number, data: unknown) => drafts[i] ?? JSON.stringify(data, null, 2)

  const setEvidence = (i: number, text: string) => {
    drafts[i] = text
    try {
      const data: unknown = JSON.parse(text)
      if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('not an object')
      const test = tests.value?.[i]
      if (test) test.evidence_data = data as Record<string, unknown>
      delete parseErrors[i]
    } catch {
      parseErrors[i] = 'Evidence must be a JSON object'
    }
  }

  const add = () => {
    tests.value = [...(tests.value ?? []), { name: '', evidence_data: {}, expect: {} }]
  }
  const remove = (i: number) => {
    const rest = (tests.value ?? []).filter((_, k) => k !== i)
    for (const box of [drafts, parseErrors])
      for (const key of Object.keys(box)) delete box[Number(key)]
    tests.value = rest.length ? rest : undefined
  }
</script>

<style scoped>
  .code :deep(textarea) {
    font-family: ui-monospace, monospace;
    font-size: 13px;
  }
</style>
