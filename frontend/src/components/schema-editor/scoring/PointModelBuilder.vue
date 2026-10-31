<template>
  <v-card variant="flat">
    <div class="d-flex align-center ga-3 flex-wrap mb-3">
      <v-combobox
        :model-value="config.engine ?? ''"
        :items="ENGINES"
        label="Scoring engine"
        density="compact"
        variant="outlined"
        class="engine"
        hide-details="auto"
        :error-messages="checks.at('scoring_configuration.engine')"
        @update:model-value="v => setText(config, 'engine', v)"
      />
      <v-spacer />
      <v-chip
        :color="errors ? 'error' : warnings ? 'warning' : 'success'"
        variant="tonal"
        :prepend-icon="errors ? 'mdi-alert-circle' : warnings ? 'mdi-alert' : 'mdi-check-circle'"
        role="status"
      >
        {{ statusText }}
      </v-chip>
      <v-btn
        variant="text"
        prepend-icon="mdi-refresh"
        :loading="checks.checking.value"
        @click="check"
      >
        Check
      </v-btn>
    </div>
    <v-alert
      v-if="checks.error.value"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-3"
      :text="checks.error.value"
    />

    <v-alert v-if="!model" type="info" variant="tonal" class="mb-3">
      This configuration has no point model of its own, so the engine's built-in model scores it.
      <template #append>
        <v-btn variant="flat" color="primary" @click="startModel">Create point model</v-btn>
      </template>
    </v-alert>

    <v-tabs v-model="tab" color="primary" density="compact">
      <v-tab v-if="model" value="sections">
        Sections
        <v-badge v-if="sectionErrors" :content="sectionErrors" color="error" inline />
      </v-tab>
      <v-tab v-if="model" value="classes">
        Bands &amp; classes
        <v-badge v-if="classErrors" :content="classErrors" color="error" inline />
      </v-tab>
      <v-tab v-if="model" value="flags">
        Review flags
        <v-badge v-if="flagErrors" :content="flagErrors" color="error" inline />
      </v-tab>
      <v-tab value="tests">
        Tests
        <v-badge v-if="failedTests" :content="failedTests" color="error" inline />
      </v-tab>
      <v-tab value="code">
        Code
        <v-badge v-if="codeError" content="!" color="error" inline />
      </v-tab>
    </v-tabs>
    <v-divider />

    <v-window v-model="tab" class="pt-4">
      <v-window-item v-if="model" value="sections">
        <PointModelSections
          v-model="model"
          :diag="checks.at"
          :count="checks.count"
          :field-definitions="fieldDefinitions"
        />
      </v-window-item>
      <v-window-item v-if="model" value="classes">
        <PointModelBands v-model="model" :diag="checks.at" :class-keys="classKeys" />
        <v-divider class="my-6" />
        <PointModelVocabulary v-model="config.classifications" :diag="checks.at" />
      </v-window-item>
      <v-window-item v-if="model" value="flags">
        <PointModelReviewFlags v-model="model" :diag="checks.at" />
      </v-window-item>
      <v-window-item value="tests">
        <PointModelTests
          v-model="config.tests"
          :results="checks.results.value"
          :running="checks.running.value"
          :class-keys="classKeys"
          @run="runTests"
        />
      </v-window-item>
      <v-window-item value="code">
        <v-textarea
          :model-value="codeText"
          label="scoring_configuration (JSON)"
          rows="18"
          auto-grow
          variant="outlined"
          class="code"
          :error-messages="codeError ? [codeError] : []"
          @update:model-value="setCode"
        />
      </v-window-item>
    </v-window>

    <v-expansion-panels v-if="checks.diagnostics.value.length" class="mt-4" variant="accordion">
      <v-expansion-panel>
        <v-expansion-panel-title
          >All diagnostics ({{ checks.diagnostics.value.length }})</v-expansion-panel-title
        >
        <v-expansion-panel-text>
          <v-list density="compact">
            <v-list-item
              v-for="(d, i) in checks.diagnostics.value"
              :key="i"
              :prepend-icon="d.severity === 'error' ? 'mdi-alert-circle' : 'mdi-alert'"
              :base-color="d.severity === 'error' ? 'error' : 'warning'"
              :title="d.message"
              :subtitle="d.field"
            />
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-card>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import PointModelBands from './PointModelBands.vue'
  import PointModelReviewFlags from './PointModelReviewFlags.vue'
  import PointModelSections from './PointModelSections.vue'
  import PointModelTests from './PointModelTests.vue'
  import PointModelVocabulary from './PointModelVocabulary.vue'
  import {
    MODEL_PATH,
    TONES,
    clone,
    setText,
    type PointModel,
    type ScoringConfig
  } from './pointModel'
  import { usePointModelChecks } from './usePointModelChecks'

  /**
   * Table builder for `scoring_configuration` (point model, bands, review flags, classes,
   * tests) with server diagnostics inline and a code view of the same object (#282).
   * Pass the schema's `fieldDefinitions` so path cross-checks see the evidence tables.
   */
  const props = defineProps<{ fieldDefinitions?: Record<string, unknown> }>()
  const value = defineModel<ScoringConfig | null>({ default: null })
  // The host blocks Save while the code view holds text that is not JSON
  const emit = defineEmits<{ error: [message: string] }>()

  // 'point_model' is the neutral alias (W10G); clingen_sop_v11 also runs any point model
  const ENGINES = ['point_model', 'clingen_sop_v11', 'gencc_based', 'qualitative_assessment']

  const config = ref<ScoringConfig>(clone(value.value ?? {}))
  const tab = ref(config.value.point_model ? 'sections' : 'tests')
  const checks = usePointModelChecks()

  const model = computed<PointModel | undefined>({
    get: () => config.value.point_model,
    set: v => (config.value.point_model = v)
  })

  // Emit copies; adopt an outside value only when it differs, so edits never loop
  const same = (a: unknown, b: unknown) => JSON.stringify(a ?? {}) === JSON.stringify(b ?? {})
  watch(
    config,
    v => {
      if (!same(v, value.value)) value.value = clone(v) // opening or re-applying is not an edit
    },
    { deep: true }
  )
  watch(value, v => {
    if (!same(v, config.value)) config.value = clone(v ?? {})
  })

  let timer: ReturnType<typeof setTimeout> | undefined
  const check = () => checks.check(config.value, props.fieldDefinitions)
  watch(
    config,
    () => {
      clearTimeout(timer)
      timer = setTimeout(check, 600)
    },
    { deep: true }
  )
  onMounted(check)
  onBeforeUnmount(() => clearTimeout(timer))

  const runTests = () => checks.runTests(config.value, props.fieldDefinitions)
  // results describe the tests as they were run
  watch(
    () => JSON.stringify(config.value.tests ?? []),
    () => (checks.results.value = [])
  )

  const startModel = () => {
    config.value.point_model = { sections: [], bands: [{ class: 'no_known' }] }
    tab.value = 'sections'
  }

  const classKeys = computed(() => {
    const keys = (config.value.classifications ?? []).map(c => c.key)
    return keys.length ? keys : TONES // the ClinGen classes
  })

  const sectionErrors = computed(() =>
    checks.count(`${MODEL_PATH}.sections`, `${MODEL_PATH}.total_cap`)
  )
  const classErrors = computed(() =>
    checks.count(
      `${MODEL_PATH}.bands`,
      `${MODEL_PATH}.overrides`,
      'scoring_configuration.classifications'
    )
  )
  const flagErrors = computed(() => checks.count(`${MODEL_PATH}.review_flags`))
  const failedTests = computed(() => checks.results.value.filter(r => r.failures.length).length)
  const errors = computed(() => checks.diagnostics.value.filter(d => d.severity === 'error').length)
  const warnings = computed(() => checks.diagnostics.value.length - errors.value)
  const statusText = computed(() =>
    errors.value
      ? `${errors.value} error${errors.value === 1 ? '' : 's'}`
      : warnings.value
        ? `${warnings.value} warning${warnings.value === 1 ? '' : 's'}`
        : 'No problems'
  )

  // Code view: the same object; text that is not valid JSON stays until fixed
  const codeDraft = ref<string | null>(null)
  const codeError = ref('')
  const codeText = computed(() => codeDraft.value ?? JSON.stringify(config.value, null, 2))
  const setCode = (text: string) => {
    codeDraft.value = text
    try {
      const parsed: unknown = JSON.parse(text)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
      config.value = parsed as ScoringConfig
      codeError.value = ''
    } catch {
      codeError.value = 'Not a JSON object; the tables keep the last valid version'
    }
  }
  watch(tab, () => {
    if (!codeError.value) codeDraft.value = null
  })
  watch(codeError, message => emit('error', message))
</script>

<style scoped>
  .engine {
    max-width: 280px;
  }
  .code :deep(textarea) {
    font-family: ui-monospace, monospace;
    font-size: 13px;
  }
</style>
