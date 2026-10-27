<template>
  <div class="d-flex flex-wrap ga-2 align-center mb-4">
    <v-select
      v-model="templateId"
      :items="templateItems"
      label="Prompt template"
      density="compact"
      hide-details
      style="max-width: 420px"
    />
    <v-btn variant="outlined" prepend-icon="mdi-plus" @click="showTemplate = true">
      New template
    </v-btn>
  </div>

  <DataTable
    v-if="templateId"
    v-model:search="search"
    v-model:page="page"
    v-model:items-per-page="itemsPerPage"
    v-model:sort-by="sortBy"
    v-model:density="density"
    storage-key="llm-prompt-versions"
    :headers="HEADERS"
    :items="shown"
    :items-length="total"
    :loading="store.loading"
    empty-text="No versions yet. Use New draft to write the first one."
  >
    <template #toolbar-actions>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openEditor(null)">New draft</v-btn>
    </template>
    <template #item.published_at="{ item }">
      <v-chip v-if="item.published_at" size="small" color="success">
        Published {{ formatDate(item.published_at) }}
      </v-chip>
      <v-chip v-else size="small">Draft</v-chip>
    </template>
    <template #item.sha256="{ item }">
      <code v-if="item.sha256">{{ item.sha256.slice(0, 12) }}</code>
    </template>
    <template #item.actions="{ item }">
      <v-btn
        size="small"
        variant="text"
        :aria-label="`${item.published_at ? 'View' : 'Edit'} version ${item.version}`"
        @click="openEditor(item)"
      >
        {{ item.published_at ? 'View' : 'Edit' }}
      </v-btn>
      <v-btn
        v-if="store.versions.length > 1"
        size="small"
        variant="text"
        :aria-label="`Diff version ${item.version}`"
        @click="openDiff(item)"
      >
        Diff
      </v-btn>
      <v-btn
        v-if="!item.published_at"
        size="small"
        variant="text"
        color="primary"
        :aria-label="`Publish version ${item.version}`"
        @click="publish(item)"
      >
        Publish
      </v-btn>
    </template>
  </DataTable>
  <p v-else class="text-body-medium text-medium-emphasis">
    Pick a template or create one to manage its versions.
  </p>

  <BaseDialog v-model="showTemplate" title="New prompt template" size="sm">
    <v-text-field
      v-model="newTemplate.key"
      label="Key"
      :rules="[keyRule]"
      hint="Lowercase letters, digits, . _ -"
      persistent-hint
      class="mb-2"
    />
    <v-select v-model="newTemplate.strategy" :items="['skeptic', 'advocate']" label="Strategy" />
    <v-textarea v-model="newTemplate.description" label="Description" rows="2" />
    <template #actions>
      <v-btn variant="text" @click="showTemplate = false">Cancel</v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :disabled="keyRule(newTemplate.key) !== true"
        @click="createTemplate"
      >
        Create
      </v-btn>
    </template>
  </BaseDialog>

  <BaseDialog v-model="showEditor" :title="editorTitle" size="lg">
    <v-alert v-if="readonly" type="info" variant="tonal" density="compact" class="mb-4">
      Published versions are read-only. Edit as new draft to change the text.
    </v-alert>
    <p class="text-body-small text-medium-emphasis mb-2">
      Placeholders use plain <code>{name}</code> substitution from the server allowlist.
    </p>
    <v-textarea v-model="draft.system_text" label="System prompt" rows="6" :readonly="readonly" />
    <v-textarea v-model="draft.user_text" label="User prompt" rows="6" :readonly="readonly" />
    <v-textarea
      v-model="draft.output_schema"
      label="Output schema (JSON object)"
      rows="4"
      :readonly="readonly"
      :error-messages="jsonError('output_schema')"
    />
    <v-textarea
      v-model="draft.few_shot_examples"
      label="Few-shot examples (JSON array)"
      rows="4"
      :readonly="readonly"
      :error-messages="jsonError('few_shot_examples')"
    />
    <template #actions>
      <v-btn variant="text" @click="showEditor = false">Close</v-btn>
      <v-btn v-if="readonly" color="primary" variant="flat" @click="readonly = false">
        Edit as new draft
      </v-btn>
      <v-btn
        v-else
        color="primary"
        variant="flat"
        :loading="saving"
        :disabled="!canSave"
        @click="saveDraft"
      >
        Save draft
      </v-btn>
    </template>
  </BaseDialog>

  <BaseDialog v-model="showDiff" :title="`Diff of version ${diffTarget?.version ?? ''}`" size="lg">
    <v-select
      v-model="against"
      :items="againstItems"
      label="Compare against"
      density="compact"
      @update:model-value="loadDiff"
    />
    <template v-if="diff">
      <p v-if="diff.output_schema_changed || diff.few_shot_examples_changed" class="mb-2">
        Also changed:
        {{
          [
            diff.output_schema_changed && 'output schema',
            diff.few_shot_examples_changed && 'few-shot examples'
          ]
            .filter(Boolean)
            .join(', ')
        }}
      </p>
      <h3 class="text-title-small">System prompt</h3>
      <pre class="llm-diff" data-test="system-diff">{{ diff.system_diff || 'No change' }}</pre>
      <h3 class="text-title-small">User prompt</h3>
      <pre class="llm-diff" data-test="user-diff">{{ diff.user_diff || 'No change' }}</pre>
    </template>
    <template #actions>
      <v-btn variant="text" @click="showDiff = false">Close</v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, toRef, watch } from 'vue'
  import DataTable from '@/components/common/DataTable.vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useConfirm } from '@/composables/useConfirm'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { llmErrorMessage, useLlmStore, type PromptVersion } from '@/stores/llm'
  import { formatDate } from '@/utils/format'
  import type { Schema } from '@/types/api'
  import { useLlmTable } from './useLlmTable'

  const HEADERS = [
    { title: 'Version', key: 'version', hideable: false },
    { title: 'Status', key: 'published_at' },
    { title: 'SHA-256', key: 'sha256', sortable: false },
    { title: '', key: 'actions', sortable: false, hideable: false, align: 'end' }
  ]

  // Mirrors TemplateCreate.key in backend/app/schemas/llm.py
  const KEY = /^[a-z0-9][a-z0-9_.-]{0,99}$/
  const keyRule = (v: string) =>
    KEY.test(v.trim()) || 'Start with a lowercase letter or digit; then a-z, 0-9, . _ -'

  const store = useLlmStore()
  const { confirm } = useConfirm()
  const { search, page, itemsPerPage, sortBy, density, shown, total } = useLlmTable(
    'prompts',
    toRef(store, 'versions')
  )

  const templateId = ref<string | null>(null)
  const templateItems = computed(() =>
    store.templates.map(t => ({ title: `${t.key} (${t.strategy})`, value: t.id }))
  )
  watch(templateId, id => {
    if (id) void store.fetchVersions(id)
  })

  const showTemplate = ref(false)
  const newTemplate = reactive<Schema<'TemplateCreate'>>({
    key: '',
    strategy: 'skeptic',
    description: ''
  })
  async function createTemplate(): Promise<void> {
    if (keyRule(newTemplate.key) !== true) return
    try {
      const row = await store.createTemplate({ ...newTemplate, key: newTemplate.key.trim() })
      showTemplate.value = false
      newTemplate.key = ''
      newTemplate.description = ''
      templateId.value = row.id
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to create template'))
    }
  }

  // JSON fields are edited as text and parsed on save
  const draft = reactive({
    system_text: '',
    user_text: '',
    output_schema: '{}',
    few_shot_examples: '[]'
  })
  const editing = ref<PromptVersion | null>(null)
  const readonly = ref(false)
  const showEditor = ref(false)
  const saving = ref(false)
  const editorTitle = computed(() =>
    editing.value ? `Prompt version ${editing.value.version}` : 'New prompt draft'
  )

  function parse(field: 'output_schema' | 'few_shot_examples'): unknown {
    try {
      const value: unknown = JSON.parse(draft[field])
      const ok =
        field === 'output_schema'
          ? !!value && typeof value === 'object' && !Array.isArray(value)
          : Array.isArray(value)
      return ok ? value : undefined
    } catch {
      return undefined
    }
  }
  const jsonError = (field: 'output_schema' | 'few_shot_examples') =>
    parse(field) === undefined
      ? field === 'output_schema'
        ? 'Must be a JSON object'
        : 'Must be a JSON array'
      : []
  const canSave = computed(
    () =>
      !!draft.system_text.trim() &&
      !!draft.user_text.trim() &&
      parse('output_schema') !== undefined &&
      parse('few_shot_examples') !== undefined
  )

  function openEditor(row: PromptVersion | null): void {
    editing.value = row
    readonly.value = !!row?.published_at
    Object.assign(draft, {
      system_text: row?.system_text ?? '',
      user_text: row?.user_text ?? '',
      output_schema: JSON.stringify(row?.output_schema ?? {}, null, 2),
      few_shot_examples: JSON.stringify(row?.few_shot_examples ?? [], null, 2)
    })
    showEditor.value = true
  }

  async function saveDraft(): Promise<void> {
    if (!templateId.value || !canSave.value) return
    saving.value = true
    try {
      const row = await store.saveVersion(templateId.value, editing.value?.id ?? null, {
        system_text: draft.system_text,
        user_text: draft.user_text,
        output_schema: parse('output_schema') as Record<string, unknown>,
        few_shot_examples: parse('few_shot_examples') as unknown[],
        lock_version: editing.value?.lock_version
      })
      showEditor.value = false
      showSuccess(`Draft version ${row.version} saved`)
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to save draft'))
    } finally {
      saving.value = false
    }
  }

  async function publish(row: PromptVersion): Promise<void> {
    const ok = await confirm({
      title: `Publish version ${row.version}?`,
      text: 'Published versions cannot be changed or unpublished. Later edits create a new draft.',
      confirmText: 'Publish'
    })
    if (!ok) return
    try {
      await store.publishVersion(row)
      showSuccess(`Version ${row.version} published`)
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to publish'))
    }
  }

  const showDiff = ref(false)
  const diffTarget = ref<PromptVersion | null>(null)
  const against = ref<string | null>(null)
  const diff = ref<Schema<'VersionDiff'> | null>(null)
  const againstItems = computed(() =>
    store.versions
      .filter(v => v.id !== diffTarget.value?.id)
      .map(v => ({ title: `Version ${v.version}`, value: v.id }))
  )

  async function loadDiff(): Promise<void> {
    if (!diffTarget.value || !against.value) return
    try {
      diff.value = await store.diffVersions(diffTarget.value.id, against.value)
    } catch (err) {
      showError(llmErrorMessage(err, 'Failed to load diff'))
    }
  }

  function openDiff(row: PromptVersion): void {
    diffTarget.value = row
    diff.value = null
    // Default: the next older version, else the closest other one
    const older = store.versions.find(v => v.version < row.version)
    against.value = (older ?? store.versions.find(v => v.id !== row.id))?.id ?? null
    showDiff.value = true
    void loadDiff()
  }
</script>

<style scoped>
  .llm-diff {
    white-space: pre-wrap;
    font-size: 0.8125rem;
    background: rgb(var(--v-theme-surface-variant), 0.4);
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 12px;
  }
</style>
