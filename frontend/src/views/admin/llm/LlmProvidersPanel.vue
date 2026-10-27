<template>
  <DataTable
    v-model:search="search"
    v-model:page="page"
    v-model:items-per-page="itemsPerPage"
    v-model:sort-by="sortBy"
    v-model:density="density"
    storage-key="llm-providers"
    :headers="HEADERS"
    :items="shown"
    :items-length="total"
    :loading="store.loading"
    empty-text="No providers yet. Use New provider to add one."
  >
    <template #toolbar-actions>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openEdit(null)">New provider</v-btn>
    </template>
    <template #item.enabled="{ item }">{{ item.enabled ? 'Yes' : 'No' }}</template>
    <template #item.has_key="{ item }">
      <span v-if="item.has_key" data-test="key-status">
        Set <code>{{ item.key_fingerprint }}</code>
      </span>
      <span v-else data-test="key-status" class="text-medium-emphasis">No key</span>
    </template>
    <template #item.actions="{ item }">
      <v-btn size="small" variant="text" :aria-label="`Edit ${item.name}`" @click="openEdit(item)">
        Edit
      </v-btn>
      <v-btn
        size="small"
        variant="text"
        :aria-label="`Set key for ${item.name}`"
        @click="openKey(item)"
      >
        {{ item.has_key ? 'Replace key' : 'Set key' }}
      </v-btn>
      <v-btn
        size="small"
        variant="text"
        :loading="pinging === item.id"
        :aria-label="`Test ${item.name}`"
        @click="ping(item)"
      >
        Test ping
      </v-btn>
    </template>
  </DataTable>

  <BaseDialog v-model="showEdit" :title="editing ? 'Edit provider' : 'New provider'" size="md">
    <v-form ref="editForm" @submit.prevent="save">
      <v-text-field v-model="form.name" label="Name" :rules="[required]" maxlength="100" />
      <v-select
        v-model="form.kind"
        :items="KINDS"
        label="Kind"
        :disabled="!!editing"
        hint="Fixed after creation"
        persistent-hint
        class="mb-2"
      />
      <v-text-field v-model="form.base_url" label="Base URL" :rules="[required]" maxlength="2048" />
      <v-alert
        v-if="urlChangeDropsKey"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-2"
        data-test="base-url-warning"
      >
        Changing the base URL deletes the stored API key. Set the key again after saving.
      </v-alert>
      <v-checkbox v-model="form.enabled" label="Enabled" hide-details />
    </v-form>
    <template #actions>
      <v-btn variant="text" @click="showEdit = false">Cancel</v-btn>
      <v-btn color="primary" variant="flat" :loading="saving" @click="save">Save</v-btn>
    </template>
  </BaseDialog>

  <BaseDialog v-model="showKey" :title="`API key for ${keyFor?.name ?? ''}`" size="md">
    <p class="mb-4">
      The key is stored encrypted and is never shown again; only its fingerprint is listed.
      {{ keyFor?.has_key ? 'Saving replaces the current key.' : '' }}
    </p>
    <v-text-field
      v-model="apiKey"
      label="API key"
      type="password"
      autocomplete="off"
      data-test="api-key-input"
      maxlength="4096"
    />
    <template #actions>
      <v-btn variant="text" @click="closeKey">Cancel</v-btn>
      <v-btn color="primary" variant="flat" :loading="saving" :disabled="!apiKey" @click="saveKey">
        Save key
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, toRef } from 'vue'
  import DataTable from '@/components/common/DataTable.vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { llmErrorMessage, useLlmStore, type LlmProvider } from '@/stores/llm'
  import type { Schema } from '@/types/api'
  import { useLlmTable } from './useLlmTable'

  const HEADERS = [
    { title: 'Name', key: 'name', hideable: false },
    { title: 'Kind', key: 'kind' },
    { title: 'Base URL', key: 'base_url' },
    { title: 'Enabled', key: 'enabled' },
    { title: 'Key', key: 'has_key', sortable: false },
    { title: '', key: 'actions', sortable: false, hideable: false, align: 'end' }
  ]
  const KINDS = ['openai_compatible', 'anthropic', 'mock']
  const required = (v: string) => !!v?.trim() || 'Required'

  const store = useLlmStore()
  const { search, page, itemsPerPage, sortBy, density, shown, total } = useLlmTable(
    'providers',
    toRef(store, 'providers')
  )

  const showEdit = ref(false)
  const editing = ref<LlmProvider | null>(null)
  const form = reactive<Schema<'ProviderCreate'>>({
    name: '',
    kind: 'openai_compatible',
    base_url: '',
    enabled: true
  })
  const editForm = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const saving = ref(false)
  const urlChangeDropsKey = computed(
    () => !!editing.value?.has_key && form.base_url.trim() !== editing.value.base_url
  )

  function openEdit(row: LlmProvider | null): void {
    editing.value = row
    const { name, kind, base_url, enabled } = row ?? {
      name: '',
      kind: 'openai_compatible' as const,
      base_url: '',
      enabled: true
    }
    Object.assign(form, { name, kind, base_url, enabled })
    showEdit.value = true
  }

  async function save(): Promise<void> {
    if (editForm.value && !(await editForm.value.validate()).valid) return
    saving.value = true
    try {
      const values = {
        name: form.name.trim(),
        base_url: form.base_url.trim(),
        enabled: form.enabled
      }
      await store.saveProvider(
        editing.value?.id ?? null,
        editing.value
          ? { ...values, lock_version: editing.value.lock_version }
          : { ...values, kind: form.kind }
      )
      showEdit.value = false
      showSuccess('Provider saved')
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to save provider'))
    } finally {
      saving.value = false
    }
  }

  const showKey = ref(false)
  const keyFor = ref<LlmProvider | null>(null)
  const apiKey = ref('')

  function openKey(row: LlmProvider): void {
    keyFor.value = row
    apiKey.value = ''
    showKey.value = true
  }

  function closeKey(): void {
    apiKey.value = ''
    showKey.value = false
  }

  async function saveKey(): Promise<void> {
    if (!keyFor.value || !apiKey.value) return
    saving.value = true
    try {
      await store.setKey(keyFor.value.id, apiKey.value)
      showSuccess('API key saved')
      closeKey()
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to save API key'))
    } finally {
      apiKey.value = '' // a failed save also forgets the key; the admin pastes it again
      saving.value = false
    }
  }

  const pinging = ref<string | null>(null)
  async function ping(row: LlmProvider): Promise<void> {
    pinging.value = row.id
    try {
      const r = await store.ping(row.id)
      if (r.ok) showSuccess(`${row.name}: ${r.model} answered in ${r.latency_ms} ms`)
      else showError(`${row.name}: ping failed (${r.error_code ?? 'unknown error'})`)
    } catch (err) {
      showError(llmErrorMessage(err, 'Ping failed'))
    } finally {
      pinging.value = null
    }
  }
</script>
