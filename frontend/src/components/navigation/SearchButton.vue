<template>
  <v-btn icon variant="text" aria-label="Search" @click="search.open()">
    <v-icon>mdi-magnify</v-icon>
  </v-btn>
</template>

<script setup lang="ts">
  import { useSearchStore } from '@/stores/search'

  const search = useSearchStore()
</script>
