<template>
  <div class="source-cell">
    <span v-if="label" class="source-cell__label text-body-small text-medium-emphasis">{{
      label
    }}</span>
    <v-chip
      v-for="(source, i) in sources"
      :key="`${i}:${source.kind}:${source.id}`"
      size="small"
      variant="tonal"
      :href="sourceHref(source)"
      :target="sourceHref(source) ? '_blank' : undefined"
      rel="noopener noreferrer"
      :title="sourceDetail(source)"
      :closable="!readonly && !disabled"
      :close-label="`Remove ${sourceLabel(source)}`"
      @click:close="remove(i)"
    >
      {{ sourceLabel(source) }}
    </v-chip>
    <span v-if="(readonly || disabled) && !sources.length">—</span>
    <div v-if="!readonly && !disabled" class="source-cell__add">
      <input
        v-model="ident"
        :aria-label="`${ariaLabel ?? 'Source'}: add an id`"
        :aria-invalid="!!error"
        :aria-describedby="hintId"
        placeholder="PMID, DOI, VCV, CA, or OMIM:600123"
        @keydown.enter.prevent="add"
      />
      <span :id="hintId" class="source-cell__kind text-body-small" aria-live="polite">{{
        detected
      }}</span>
      <button type="button" :disabled="!ident.trim()" @click="add">Add</button>
      <span v-if="error" class="source-cell__error" role="alert">{{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  /** `source` cell or list field (#593): sources as link chips; type an id, its kind is read from it. */
  import { computed, getCurrentInstance, ref } from 'vue'
  import {
    SOURCE_KINDS,
    detectSource,
    sourceDetail,
    sourceError,
    sourceHref,
    sourceLabel,
    sourceList,
    type Source
  } from './sourceModel'

  // Table cells pass editor props (rules, density, variant) this cell does not use
  defineOptions({ inheritAttrs: false })
  const props = defineProps<{
    modelValue?: unknown
    readonly?: boolean
    disabled?: boolean
    ariaLabel?: string
    label?: string
  }>()
  const emit = defineEmits<{ 'update:model-value': [sources: Source[]] }>()

  const sources = computed(() => sourceList(props.modelValue))
  const ident = ref('')
  const error = ref('')
  const hintId = `source-kind-${getCurrentInstance()?.uid}`
  // The kind the typed id reads as, shown beside it before it is added
  const detected = computed(() => {
    if (!ident.value.trim()) return ''
    const { kind } = detectSource(ident.value)
    return SOURCE_KINDS.find(k => k.value === kind)?.title ?? kind
  })

  function add() {
    const source = detectSource(ident.value)
    error.value = sourceError(source.kind, source.id)
    if (error.value) return
    emit('update:model-value', [...sources.value, source])
    ident.value = ''
  }

  function remove(index: number) {
    emit(
      'update:model-value',
      sources.value.filter((_, i) => i !== index)
    )
  }
</script>

<style scoped>
  .source-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
    align-items: center;
    min-width: 12rem;
  }

  .source-cell__add {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .source-cell__add input {
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    min-width: 0;
    max-width: 11rem;
  }

  .source-cell__kind {
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .source-cell__error {
    color: rgb(var(--v-theme-error));
    font-size: 0.75rem;
  }
</style>
