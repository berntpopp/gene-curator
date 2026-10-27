<template>
  <v-card variant="outlined" :loading="loading" data-test="scope-llm-settings">
    <v-card-title class="text-title-large">LLM assistance</v-card-title>
    <v-card-text>
      <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">{{ loadError }}</v-alert>
      <template v-else-if="form">
        <p class="text-body-medium text-medium-emphasis mb-4">
          Opt this scope in to LLM-assisted review. Only models and published prompt versions a
          platform admin enabled are offered. A cap of 0 means no limit.
        </p>
        <v-switch v-model="form.enabled" label="Enabled for this scope" color="primary" inset />
        <v-select
          v-model="form.model_id"
          :items="modelItems"
          label="Model"
          clearable
          :error-messages="form.enabled && !form.model_id ? 'Enabling requires a model' : []"
          no-data-text="No model is enabled yet"
        />
        <v-row>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.skeptic_prompt_version_id"
              :items="promptItems('skeptic')"
              label="Skeptic prompt version"
              clearable
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="form.advocate_prompt_version_id"
              :items="promptItems('advocate')"
              label="Advocate prompt version"
              clearable
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="form.monthly_token_cap"
              label="Monthly token cap"
              type="number"
              min="0"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="form.monthly_cost_cap_cents"
              label="Monthly cost cap (cents)"
              type="number"
              min="0"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="form.daily_run_cap"
              label="Daily run cap"
              type="number"
              min="0"
            />
          </v-col>
        </v-row>
      </template>
    </v-card-text>
    <v-card-actions v-if="form">
      <v-spacer />
      <v-btn
        color="primary"
        variant="flat"
        :loading="saving"
        :disabled="form.enabled && !form.model_id"
        @click="save"
      >
        Save LLM settings
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { llmErrorMessage, useLlmStore } from '@/stores/llm'
  import type { Schema } from '@/types/api'

  const props = defineProps<{ scopeId: string }>()

  const store = useLlmStore()
  const form = ref<Schema<'ScopeSettingsUpdate'> | null>(null)
  const options = ref<Schema<'ScopeLLMOptions'>>({ models: [], prompt_versions: [] })
  const loading = ref(false)
  const loadError = ref<string | null>(null)
  const saving = ref(false)

  const modelItems = computed(() =>
    options.value.models.map(m => ({ title: `${m.model_id} (${m.provider_name})`, value: m.id }))
  )
  const promptItems = (strategy: 'skeptic' | 'advocate') =>
    options.value.prompt_versions
      .filter(v => v.strategy === strategy)
      .map(v => ({ title: `${v.template_key} v${v.version}`, value: v.id }))

  const toForm = (s: Schema<'ScopeSettingsOut'>): Schema<'ScopeSettingsUpdate'> => ({
    lock_version: s.lock_version,
    enabled: s.enabled,
    model_id: s.model_id ?? null,
    skeptic_prompt_version_id: s.skeptic_prompt_version_id ?? null,
    advocate_prompt_version_id: s.advocate_prompt_version_id ?? null,
    monthly_token_cap: s.monthly_token_cap,
    monthly_cost_cap_cents: s.monthly_cost_cap_cents,
    daily_run_cap: s.daily_run_cap
  })

  async function load(): Promise<void> {
    loading.value = true
    loadError.value = null
    try {
      const [opts, settings] = await Promise.all([
        store.scopeOptions(props.scopeId),
        store.scopeSettings(props.scopeId)
      ])
      options.value = opts
      form.value = toForm(settings)
    } catch (err) {
      loadError.value = llmErrorMessage(err, 'Failed to load LLM settings')
    } finally {
      loading.value = false
    }
  }

  async function save(): Promise<void> {
    if (!form.value) return
    saving.value = true
    try {
      form.value = toForm(await store.saveScopeSettings(props.scopeId, form.value))
      showSuccess('LLM settings saved')
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to save LLM settings'))
    } finally {
      saving.value = false
    }
  }

  onMounted(load)
</script>
