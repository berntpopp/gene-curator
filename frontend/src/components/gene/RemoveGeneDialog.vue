<template>
  <v-dialog
    :model-value="modelValue"
    max-width="450"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card>
      <v-card-title class="d-flex align-center text-error pa-4">
        <v-icon start color="error" size="28">mdi-alert-circle</v-icon>
        <span class="text-h6">Remove Gene from Scope</span>
      </v-card-title>

      <v-divider />

      <v-card-text class="pa-4">
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
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-btn variant="text" :disabled="isRemoving" @click="emit('cancel')"> Cancel </v-btn>
        <v-spacer />
        <v-btn color="error" variant="flat" :loading="isRemoving" @click="emit('confirm')">
          <v-icon start>mdi-delete</v-icon>
          Remove
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
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
