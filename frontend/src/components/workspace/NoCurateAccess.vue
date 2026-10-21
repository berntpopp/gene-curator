<template>
  <v-alert type="warning" variant="tonal" prominent data-testid="no-curate-access">
    <v-alert-title>You cannot start this here</v-alert-title>
    Starting a precuration or curation needs a curator or admin role in this scope.
    <template #append>
      <v-btn variant="outlined" :to="`/scopes/${scopeId}`">Back to scope</v-btn>
    </template>
  </v-alert>
</template>

<script setup lang="ts">
  defineProps<{ scopeId: string }>()
</script>
