<template>
  <DataTable
    v-model:search="search"
    v-model:page="page"
    v-model:items-per-page="itemsPerPage"
    v-model:sort-by="sortBy"
    v-model:density="density"
    storage-key="llm-models"
    :headers="HEADERS"
    :items="shown"
    :items-length="total"
    :loading="store.loading"
    empty-text="No models yet. Add a provider first, then use New model."
  >
    <template #toolbar-actions>
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        :disabled="!store.providers.length"
        @click="openEdit(null)"
      >
        New model
      </v-btn>
    </template>
    <template #item.provider_id="{ item }">{{ providerName(item.provider_id) }}</template>
    <template #item.uses_max_completion_tokens="{ item }">
      {{ item.uses_max_completion_tokens ? 'Yes' : 'No' }}
    </template>
    <template #item.enabled="{ item }">{{ item.enabled ? 'Yes' : 'No' }}</template>
    <template #item.actions="{ item }">
      <v-btn
        size="small"
        variant="text"
        :aria-label="`Edit ${item.model_id}`"
        @click="openEdit(item)"
      >
        Edit
      </v-btn>
    </template>
  </DataTable>

  <BaseDialog v-model="show" :title="editing ? `Edit ${editing.model_id}` : 'New model'" size="md">
    <v-form ref="formRef" @submit.prevent="save">
      <template v-if="!editing">
        <v-select
          v-model="form.provider_id"
          :items="store.providers"
          item-title="name"
          item-value="id"
          label="Provider"
          :rules="[required]"
        />
        <v-text-field
          v-model="form.model_id"
          label="Model ID (dated)"
          hint="Pin a dated release, e.g. claude-sonnet-4-5-20250929 or gpt-4o-2024-08-06"
          persistent-hint
          :rules="[required, dated]"
          maxlength="200"
          class="mb-2"
        />
      </template>
      <v-row>
        <v-col cols="6">
          <v-text-field
            v-model="form.input_price_per_mtok_cents"
            label="Input price (cents per 1M tokens)"
            type="number"
            min="0"
            :rules="[required, nonNegative]"
          />
        </v-col>
        <v-col cols="6">
          <v-text-field
            v-model="form.output_price_per_mtok_cents"
            label="Output price (cents per 1M tokens)"
            type="number"
            min="0"
            :rules="[required, nonNegative]"
          />
        </v-col>
        <v-col cols="6">
          <v-text-field
            v-model.number="form.max_tokens"
            label="Max output tokens"
            type="number"
            min="1"
            max="200000"
            :rules="[intIn(1, 200_000)]"
          />
        </v-col>
        <v-col cols="6">
          <v-text-field
            v-model.number="form.timeout_s"
            label="Timeout (s)"
            type="number"
            min="30"
            max="60"
            :rules="[intIn(30, 60)]"
            hint="30 to 60 seconds"
            persistent-hint
          />
        </v-col>
      </v-row>
      <v-checkbox
        v-model="form.uses_max_completion_tokens"
        label="o-series model (sends max_completion_tokens)"
        hide-details
      />
      <v-checkbox v-model="form.enabled" label="Enabled" hide-details />
    </v-form>
    <template #actions>
      <v-btn variant="text" @click="show = false">Cancel</v-btn>
      <v-btn color="primary" variant="flat" :loading="saving" @click="save">Save</v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import { reactive, ref, toRef } from 'vue'
  import DataTable from '@/components/common/DataTable.vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { llmErrorMessage, useLlmStore, type LlmModel } from '@/stores/llm'
  import { useLlmTable } from './useLlmTable'

  const HEADERS = [
    { title: 'Model ID', key: 'model_id', hideable: false },
    { title: 'Provider', key: 'provider_id' },
    { title: 'Input ¢/1M', key: 'input_price_per_mtok_cents' },
    { title: 'Output ¢/1M', key: 'output_price_per_mtok_cents' },
    { title: 'Max tokens', key: 'max_tokens' },
    { title: 'Timeout (s)', key: 'timeout_s' },
    { title: 'o-series', key: 'uses_max_completion_tokens' },
    { title: 'Enabled', key: 'enabled' },
    { title: '', key: 'actions', sortable: false, hideable: false, align: 'end' }
  ]
  // Mirrors the backend DATED_MODEL_ID pattern (schemas/llm.py)
  const DATED = /^[A-Za-z0-9][A-Za-z0-9._:/-]*(\d{8}|\d{4}-\d{2}-\d{2})$/
  const required = (v: string) => !!String(v ?? '').trim() || 'Required'
  const dated = (v: string) => DATED.test(v ?? '') || 'Must end in a release date'
  const nonNegative = (v: string | number) => Number(v) >= 0 || 'Must be 0 or more'
  // v-model.number leaves an empty field as '', which must never reach the API
  const intIn = (min: number, max: number) => (v: unknown) =>
    (Number.isInteger(v) && (v as number) >= min && (v as number) <= max) ||
    `Whole number from ${min} to ${max}`

  const store = useLlmStore()
  const { search, page, itemsPerPage, sortBy, density, shown, total } = useLlmTable(
    'models',
    toRef(store, 'models')
  )
  const providerName = (id: string) => store.providers.find(p => p.id === id)?.name ?? id

  const blank = () => ({
    provider_id: '',
    model_id: '',
    input_price_per_mtok_cents: '0' as string | number,
    output_price_per_mtok_cents: '0' as string | number,
    max_tokens: 4096,
    timeout_s: 60,
    uses_max_completion_tokens: false,
    enabled: true
  })
  const show = ref(false)
  const editing = ref<LlmModel | null>(null)
  const form = reactive(blank())
  const formRef = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const saving = ref(false)

  function openEdit(row: LlmModel | null): void {
    editing.value = row
    const src = row ?? blank()
    Object.assign(form, {
      provider_id: src.provider_id,
      model_id: src.model_id,
      input_price_per_mtok_cents: src.input_price_per_mtok_cents,
      output_price_per_mtok_cents: src.output_price_per_mtok_cents,
      max_tokens: src.max_tokens,
      timeout_s: src.timeout_s,
      uses_max_completion_tokens: src.uses_max_completion_tokens,
      enabled: src.enabled
    })
    show.value = true
  }

  async function save(): Promise<void> {
    if (formRef.value && !(await formRef.value.validate()).valid) return
    saving.value = true
    const { provider_id, model_id, ...values } = form
    try {
      await store.saveModel(
        editing.value?.id ?? null,
        editing.value
          ? { ...values, lock_version: editing.value.lock_version }
          : { ...values, provider_id, model_id: model_id.trim() }
      )
      show.value = false
      showSuccess('Model saved')
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to save model'))
    } finally {
      saving.value = false
    }
  }
</script>
