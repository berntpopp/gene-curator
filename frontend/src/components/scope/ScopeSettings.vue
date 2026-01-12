<!--
  Scope Settings Component (Placeholder)

  TODO: Implement full scope settings functionality
-->

<template>
  <v-card>
    <v-card-title>Scope Settings</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal">
        Scope settings component coming soon. This will allow updating scope configuration.
      </v-alert>

      <!-- Basic Information -->
      <v-card class="mt-4">
        <v-card-title>Basic Information</v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Name</v-list-item-title>
              <v-list-item-subtitle>{{ scope.name }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Display Name</v-list-item-title>
              <v-list-item-subtitle>{{ scope.display_name }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Status</v-list-item-title>
              <v-list-item-subtitle>
                {{ scope.is_active ? 'Active' : 'Inactive' }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
  import { defineProps } from 'vue'

  defineProps({
    scope: {
      type: Object,
      required: true
    }
  })
</script>
