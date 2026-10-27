<template>
  <v-btn
    size="small"
    variant="text"
    :aria-label="`Test run version ${version.version}`"
    @click="open = true"
  >
    Test run
  </v-btn>
  <BaseDialog v-model="open" :title="`Test run of version ${version.version}`" size="md">
    <p class="text-body-small text-medium-emphasis mb-2">
      Runs this version over the golden set with the chosen model. Nothing is stored.
    </p>
    <v-select
      v-model="modelId"
      :items="modelItems"
      label="Model"
      density="compact"
      data-test="test-run-model"
    />
    <template v-if="result">
      <p class="mb-2" data-test="test-run-summary">
        {{ result.passed }} of {{ result.total }} cases passed with {{ result.model }}
      </p>
      <v-table density="compact">
        <thead>
          <tr>
            <th>Case</th>
            <th>Result</th>
            <th>Tokens in / out</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in result.cases" :key="c.case">
            <td>{{ c.case }}</td>
            <td>
              <v-chip size="small" :color="c.ok ? 'success' : 'error'">
                {{ c.ok ? 'Passed' : (c.error_code ?? 'Failed') }}
              </v-chip>
            </td>
            <td>{{ c.input_tokens }} / {{ c.output_tokens }}</td>
          </tr>
        </tbody>
      </v-table>
    </template>
    <template #actions>
      <v-btn variant="text" @click="open = false">Close</v-btn>
      <v-btn color="primary" variant="flat" :loading="running" :disabled="!modelId" @click="run">
        Run
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { showError } from '@/composables/useNotifications'
  import { useLlmStore, type PromptVersion } from '@/stores/llm'
  import { readableApiError } from '@/utils/apiErrorText'
  import type { Schema } from '@/types/api'

  const props = defineProps<{ version: PromptVersion }>()

  const store = useLlmStore()
  const open = ref(false)
  const running = ref(false)
  const modelId = ref<string | null>(store.models.find(m => m.enabled)?.id ?? null)
  const result = ref<Schema<'TestRunOut'> | null>(null)
  const modelItems = computed(() =>
    store.models.map(m => ({ title: m.model_id, value: m.id, props: { disabled: !m.enabled } }))
  )

  async function run(): Promise<void> {
    if (!modelId.value) return
    running.value = true
    result.value = null
    try {
      result.value = await store.testRun(props.version.id, { model_id: modelId.value })
    } catch (err) {
      showError(readableApiError(err, 'Test run failed'))
    } finally {
      running.value = false
    }
  }
</script>
