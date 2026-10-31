<template>
  <div class="source-cell">
    <span v-if="label" class="source-cell__label text-body-small text-medium-emphasis">{{
      label
    }}</span>
    <span
      v-for="(source, i) in sources"
      :key="i"
      class="source-cell__item"
      :title="sourceDetail(source)"
    >
      <a
        v-if="sourceHref(source)"
        :href="sourceHref(source)"
        target="_blank"
        rel="noopener noreferrer"
        >{{ sourceLabel(source) }}</a
      >
      <span v-else>{{ sourceLabel(source) }}</span>
      <button
        v-if="!readonly && !disabled"
        type="button"
        class="source-cell__remove"
        :aria-label="`Remove ${sourceLabel(source)}`"
        @click="remove(i)"
      >
        ×
      </button>
    </span>
    <span v-if="(readonly || disabled) && !sources.length">—</span>
    <div v-if="!readonly && !disabled" class="source-cell__add">
      <select v-model="kind" :aria-label="`${ariaLabel ?? 'Source'} kind`">
        <option v-for="k in SOURCE_KINDS" :key="k.value" :value="k.value">{{ k.title }}</option>
      </select>
      <input
        v-model="ident"
        :aria-label="`${ariaLabel ?? 'Source'} id`"
        :aria-invalid="!!error"
        placeholder="id"
        @keydown.enter.prevent="add"
      />
      <button type="button" :disabled="!ident.trim()" @click="add">Add</button>
      <span v-if="error" class="source-cell__error" role="alert">{{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  /** `source` cell or list field (#593): sources as links, add by kind and id, remove each. */
  import { computed, ref } from 'vue'
  import {
    SOURCE_KINDS,
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
  const kind = ref('pmid')
  const ident = ref('')
  const error = ref('')

  function add() {
    error.value = sourceError(kind.value, ident.value)
    if (error.value) return
    emit('update:model-value', [...sources.value, { kind: kind.value, id: ident.value.trim() }])
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

  .source-cell__add input,
  .source-cell__add select {
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    min-width: 0;
    max-width: 9rem;
  }

  .source-cell__remove {
    margin-left: 2px;
  }

  .source-cell__error {
    color: rgb(var(--v-theme-error));
    font-size: 0.75rem;
  }
</style>
