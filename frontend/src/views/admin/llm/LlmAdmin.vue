<template>
  <v-container>
    <h1 class="text-headline-large mb-2">LLM configuration</h1>
    <p class="text-body-medium text-medium-emphasis mb-4">
      Providers, API keys, models, prompts and usage for LLM-assisted curation. Scopes opt in from
      their own settings.
    </p>
    <v-alert v-if="store.error" type="error" variant="tonal" class="mb-4">
      {{ store.error }}
    </v-alert>
    <v-tabs v-model="tab" color="primary" show-arrows class="mb-4">
      <v-tab value="providers">Providers and keys</v-tab>
      <v-tab value="models">Models and pricing</v-tab>
      <v-tab value="prompts">Prompts</v-tab>
      <v-tab value="usage">Usage and runs</v-tab>
    </v-tabs>
    <v-window v-model="tab">
      <v-window-item value="providers"><LlmProvidersPanel /></v-window-item>
      <v-window-item value="models"><LlmModelsPanel /></v-window-item>
      <v-window-item value="prompts"><LlmPromptsPanel /></v-window-item>
      <v-window-item value="usage"><LlmUsagePanel /></v-window-item>
    </v-window>
  </v-container>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useLlmStore } from '@/stores/llm'
  import LlmProvidersPanel from './LlmProvidersPanel.vue'
  import LlmModelsPanel from './LlmModelsPanel.vue'
  import LlmPromptsPanel from './LlmPromptsPanel.vue'
  import LlmUsagePanel from './LlmUsagePanel.vue'

  const store = useLlmStore()
  const tab = ref('providers')

  onMounted(store.fetchConfig)
</script>
