<!--
  Gene List Component (Placeholder)

  TODO: Implement full gene listing functionality
-->

<template>
  <v-card>
    <v-card-title>Genes</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal">
        Gene list component coming soon. This will display all genes assigned to the scope.
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
