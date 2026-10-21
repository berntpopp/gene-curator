<template>
  <!-- v-card, not v-alert: VAlert hard-codes role="alert", warnings must be a polite status -->
  <v-card
    v-if="messages.length && open"
    color="warning"
    variant="tonal"
    class="mt-4 px-4 py-2"
    role="status"
  >
    <div class="d-flex align-center flex-wrap ga-2">
      <v-icon icon="mdi-alert" size="small" />
      <span class="font-weight-medium">
        {{ messages.length }} {{ messages.length === 1 ? 'warning' : 'warnings' }}
      </span>
      <span class="text-body-small">These do not block saving.</span>
      <v-btn
        variant="text"
        size="small"
        density="comfortable"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Hide' : 'Show' }}
      </v-btn>
      <v-spacer />
      <v-btn
        icon="mdi-close"
        variant="text"
        size="x-small"
        aria-label="Dismiss warnings"
        @click="open = false"
      />
    </div>
    <ul v-if="expanded" class="pl-10 pb-1 text-body-small">
      <li v-for="message in messages" :key="message">{{ message }}</li>
    </ul>
  </v-card>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'

  /** Already labelled, de-duplicated warning lines ("Field: message") */
  const props = defineProps<{ messages: string[] }>()

  const open = ref(true)
  const expanded = ref(false)
  // A different set of warnings brings a dismissed alert back
  watch(
    () => props.messages.join('\n'),
    () => {
      open.value = true
    }
  )
</script>
