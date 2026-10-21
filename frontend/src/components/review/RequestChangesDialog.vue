<template>
  <BaseDialog
    :model-value="modelValue"
    size="md"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #title>
      <span class="text-title-large">Send {{ geneSymbol }} back for changes?</span>
    </template>
    <p class="text-body-medium text-medium-emphasis mb-3">
      The curation returns to the curator. Your open queries are listed as to-dos; edit as needed.
    </p>
    <v-textarea
      v-model="feedback"
      label="Feedback for the curator"
      rows="5"
      auto-grow
      variant="outlined"
    />
    <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
    <template #actions>
      <v-btn variant="text" data-testid="changes-cancel" @click="emit('update:modelValue', false)">
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :loading="busy"
        :disabled="!feedback.trim()"
        data-testid="changes-confirm"
        @click="emit('reject', feedback.trim())"
      >
        Request changes
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  /** Request changes; the feedback starts as the reviewer's open queries (the curator's to-do list). */
  import { ref, watch } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'

  const props = defineProps<{
    modelValue: boolean
    geneSymbol?: string | null
    todos: string
    busy: boolean
    error: string | null
  }>()
  const emit = defineEmits<{ 'update:modelValue': [boolean]; reject: [string] }>()

  const feedback = ref(props.todos)
  watch(
    () => [props.modelValue, props.todos] as const,
    ([open]) => {
      if (open) feedback.value = props.todos
    }
  )
</script>
