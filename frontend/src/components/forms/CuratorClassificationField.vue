<template>
  <section class="mt-6" data-testid="curator-classification" aria-label="Final classification">
    <h3 class="text-title-medium mb-1">Final classification</h3>
    <p class="text-body-small text-medium-emphasis mb-3">
      Calculated: {{ calculatedLabel || '—' }}. Leave empty to publish the calculated one; reviewers
      confirm the final classification when they approve.
    </p>
    <v-select
      :model-value="modelValue.curator_classification"
      :items="items"
      label="Curator classification"
      :placeholder="calculatedLabel ? `${calculatedLabel} (calculated)` : undefined"
      persistent-placeholder
      clearable
      variant="outlined"
      density="compact"
      :readonly="readonly"
      @update:model-value="update({ curator_classification: $event ?? null })"
    />
    <v-textarea
      v-if="differs || modelValue.curator_classification_rationale"
      :model-value="modelValue.curator_classification_rationale ?? ''"
      label="Rationale"
      :rules="differs ? [required] : []"
      :hint="differs ? 'Required: it differs from the calculated classification' : undefined"
      persistent-hint
      rows="2"
      auto-grow
      variant="outlined"
      density="compact"
      :readonly="readonly"
      @update:model-value="update({ curator_classification_rationale: $event || null })"
    />
  </section>
</template>

<script setup lang="ts">
  /** The curator's call (#533): a classification other than the calculated one, with why. */
  import { computed } from 'vue'
  import { CLASSIFICATIONS, classKey, getClassification } from '@/config/classification'

  export interface CuratorCall {
    curator_classification: string | null
    curator_classification_rationale: string | null
  }

  const props = defineProps<{
    modelValue: CuratorCall
    calculated?: string | null
    readonly?: boolean
    /** The server's classes for this curation's schema; the ClinGen list until loaded. */
    choices?: { key: string; label: string }[] | null
  }>()
  const emit = defineEmits<{ 'update:modelValue': [CuratorCall] }>()

  // The API stores the class key; a known class shows its vocabulary label, else the server's
  const items = computed(() =>
    (props.choices?.length ? props.choices : CLASSIFICATIONS).map(c => {
      const info = getClassification(c.key)
      return { title: info.key === 'unknown' ? c.label : info.label, value: c.key }
    })
  )
  const calculatedLabel = computed(() =>
    props.calculated ? getClassification(props.calculated).label : ''
  )
  // Same rule as the server: both compared as class keys
  const differs = computed(() => {
    const proposed = props.modelValue.curator_classification
    return !!proposed && classKey(proposed) !== classKey(props.calculated)
  })
  const required = (v: string) => !!v?.trim() || 'A rationale is required'

  function update(patch: Partial<CuratorCall>) {
    emit('update:modelValue', { ...props.modelValue, ...patch })
  }
</script>
