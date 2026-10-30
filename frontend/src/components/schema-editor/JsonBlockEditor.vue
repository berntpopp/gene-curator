<template>
  <v-textarea
    v-model="text"
    :label="label"
    :hint="hint"
    persistent-hint
    variant="outlined"
    rows="14"
    auto-grow
    max-rows="30"
    class="json-input"
    spellcheck="false"
    :readonly="readonly"
    :error-messages="error ? [error] : []"
    @update:model-value="parse"
  />
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'

  // One JSON block of a schema; emits only parsed objects, and the parse error (or '') each edit
  const props = defineProps<{
    modelValue: unknown
    label: string
    hint?: string
    /** Empty text means null (scoring_configuration); otherwise an object is required */
    nullable?: boolean
    readonly?: boolean
  }>()
  const emit = defineEmits<{ 'update:modelValue': [value: unknown]; error: [message: string] }>()

  const pretty = (value: unknown) => (value == null ? '' : JSON.stringify(value, null, 2))
  const text = ref(pretty(props.modelValue))
  const error = ref('')

  const read = (raw: string): unknown => {
    if (!raw.trim()) {
      if (props.nullable) return null
      throw new Error('Required: enter a JSON object, e.g. {}')
    }
    const value: unknown = JSON.parse(raw)
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error('Must be a JSON object ({ ... })')
    }
    return value
  }

  const parse = () => {
    try {
      const value = read(text.value)
      error.value = ''
      emit('update:modelValue', value)
    } catch (e) {
      error.value = (e as Error).message
    }
    emit('error', error.value)
  }

  // Another tab changed the block: show it, unless the text already says the same
  watch(
    () => JSON.stringify(props.modelValue ?? null),
    next => {
      try {
        if (JSON.stringify(read(text.value)) === next) return
      } catch {
        // invalid text is replaced by the new value below
      }
      text.value = pretty(props.modelValue)
      error.value = ''
      emit('error', '')
    }
  )
</script>

<style scoped>
  .json-input :deep(textarea) {
    font-family: var(--font-mono, monospace);
    font-size: 13px;
  }
</style>
