<template>
  <v-alert v-if="failed" type="warning" variant="tonal" prominent data-testid="no-curate-access">
    <v-alert-title>We could not check your access</v-alert-title>
    Your role in this scope could not be read. Try again.
    <template #append>
      <v-btn variant="outlined" data-testid="retry-access" @click="emit('retry')">Retry</v-btn>
    </template>
  </v-alert>
  <v-alert v-else type="warning" variant="tonal" prominent data-testid="no-curate-access">
    <v-alert-title>You cannot start this here</v-alert-title>
    Starting a precuration or curation needs a curator or admin role in this scope.
    <template #append>
      <v-btn variant="outlined" :to="`/scopes/${scopeId}`">Back to scope</v-btn>
    </template>
  </v-alert>
</template>

<script setup lang="ts">
  defineProps<{ scopeId: string; failed?: boolean }>()
  const emit = defineEmits<{ retry: [] }>()
</script>
