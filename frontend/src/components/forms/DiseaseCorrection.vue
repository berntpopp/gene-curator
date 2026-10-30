<template>
  <!-- #453: only a scope admin may correct a legacy record's disease entity, with a reason -->
  <div v-if="isAdmin && curations.currentCuration" class="mb-2">
    <v-btn
      color="warning"
      variant="tonal"
      prepend-icon="mdi-pencil"
      data-testid="disease-correction-open"
      @click="start"
    >
      Correct disease entity
    </v-btn>
    <BaseDialog v-model="open" title="Correct disease entity" persistent @cancel="open = false">
      <v-form ref="form" @submit.prevent="submit">
        <p class="text-body-medium mb-4">
          An authorized correction of this record. It is written to the audit log with the old and
          new values and your reason.
        </p>
        <v-text-field v-model="values.disease_name" label="Disease name" :rules="[filled]" />
        <v-text-field
          v-model="values.mondo_id"
          label="MONDO ID"
          placeholder="MONDO:0000000"
          :rules="[v => /^MONDO:\d{7}$/.test(v.trim()) || 'MONDO:0000000 format']"
        />
        <v-select
          v-model="values.mode_of_inheritance"
          label="Mode of inheritance"
          :items="moiItems"
          :rules="[filled]"
        />
        <v-select
          v-model="values.relationship_type"
          label="Relationship (empty: unchanged)"
          :items="relationships"
          clearable
        />
        <v-textarea
          v-model="values.reason"
          label="Reason for the correction"
          rows="2"
          :rules="[v => v.trim().length >= 3 || 'Give a reason']"
        />
        <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
      </v-form>
      <template #actions>
        <v-btn variant="text" @click="open = false">Cancel</v-btn>
        <v-btn
          color="primary"
          :loading="saving"
          data-testid="disease-correction-save"
          @click="submit"
        >
          Save correction
        </v-btn>
      </template>
    </BaseDialog>
  </div>
</template>

<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useCurationsStore } from '@/stores/curations'
  import { useScopesStore } from '@/stores/scopes'
  import { errorMessage } from '@/stores/apiError'
  import { formatInheritance } from '@/utils/inheritance'

  // The form's save: unsaved edits reach the server before the correction reloads it
  const props = defineProps<{ save: () => Promise<boolean> }>()
  const emit = defineEmits<{ corrected: [] }>()

  const curations = useCurationsStore()
  const isAdmin = computed(() => useScopesStore().currentUserRole === 'admin')
  const open = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const values = reactive({
    disease_name: '',
    mondo_id: '',
    mode_of_inheritance: '',
    relationship_type: null as 'mendelian' | 'susceptibility' | null,
    reason: ''
  })
  const moiItems = ['AD', 'AR', 'XL', 'XLD', 'XLR', 'MT', 'SD'].map(value => ({
    title: formatInheritance(value),
    value
  }))
  const relationships = [
    { title: 'Mendelian', value: 'mendelian' },
    { title: 'Susceptibility', value: 'susceptibility' }
  ]
  const filled = (v: string) => !!v?.trim() || 'Required'

  /** The record's own relationship type (flat wins, as on the server), else null. */
  function currentRelationship() {
    const evidence = (curations.currentCuration?.evidence_data ?? {}) as Record<string, unknown>
    const entity = evidence.entity_definition as Record<string, unknown> | undefined
    const raw = evidence.relationship_type || entity?.relationship_type
    return raw === 'mendelian' || raw === 'susceptibility' ? raw : null
  }

  async function start() {
    if (!(await props.save())) return // a failed save keeps the edits and opens nothing
    values.relationship_type = currentRelationship()
    error.value = null
    open.value = true
  }

  async function submit() {
    if (!(await form.value?.validate())?.valid) return
    saving.value = true
    error.value = null
    try {
      const curation = curations.currentCuration
      if (!curation) return
      await curations.correctDisease(curation.id, {
        ...values,
        lock_version: curation.lock_version ?? 0
      })
      open.value = false
      emit('corrected')
    } catch (e) {
      error.value = errorMessage(e, 'Correction failed')
    } finally {
      saving.value = false
    }
  }
</script>
