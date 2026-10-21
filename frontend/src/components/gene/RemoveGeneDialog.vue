<template>
  <BaseDialog
    :model-value="modelValue"
    persistent
    size="sm"
    @cancel="!isRemoving && emit('cancel')"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #title
      ><v-icon start color="error" size="28">mdi-alert-circle</v-icon>
      <span class="text-h6">Remove Gene from Scope</span></template
    >
    <p class="mb-3">
      Are you sure you want to remove
      <strong>{{ geneSymbol }}</strong> from this scope?
    </p>
    <v-alert type="warning" variant="tonal" density="compact">
      <div class="text-body-2">
        This will remove the gene assignment but will not delete the gene from the catalog. Any
        existing precurations or curations will be preserved.
      </div>
    </v-alert>
    <template #actions>
      <v-btn variant="text" :disabled="isRemoving" @click="emit('cancel')"> Cancel </v-btn>
      <v-btn color="error" variant="flat" :loading="isRemoving" @click="emit('confirm')">
        <v-icon start>mdi-delete</v-icon>
        Remove
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import BaseDialog from '@/components/BaseDialog.vue'
  /**
   * Confirmation dialog for removing a gene from the current scope.
   */
  defineProps<{
    modelValue: boolean
    geneSymbol?: string | null
    isRemoving: boolean
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    confirm: []
    cancel: []
  }>()
</script>
