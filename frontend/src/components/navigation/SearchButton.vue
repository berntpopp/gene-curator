<template>
  <v-btn icon variant="text" aria-label="Search" @click="openSearch">
    <v-icon>mdi-magnify</v-icon>
  </v-btn>
</template>

<script setup lang="ts">
  // ponytail: the command palette (PR #355) is not on master yet; wire open() here once it lands.
  const openSearch = () => undefined
</script>
