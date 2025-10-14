<!--
  Curation List Component (Placeholder)

  TODO: Implement full curation listing functionality
-->

<template>
  <v-card>
    <v-card-title>Curations</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal">
        Curation list component coming soon. This will display all curations for the scope.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
  import { defineProps } from 'vue'

  defineProps({
    scopeId: {
      type: String,
      required: true
    }
  })
</script>
