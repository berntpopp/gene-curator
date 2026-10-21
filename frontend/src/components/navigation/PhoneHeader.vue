<template>
  <v-app-bar flat color="surface" border="b">
    <router-link to="/" aria-label="Gene Curator home" class="mx-3">
      <v-img src="/img/logo.png" alt="" width="28" max-width="28" max-height="28" contain />
    </router-link>
    <h1 class="text-title-large header-title">{{ title }}</h1>
    <v-spacer />
    <SearchButton />
    <ThemeToggle />
  </v-app-bar>
</template>

<script setup lang="ts">
  /** Signed-in phone page header (Phone.png): page title from route meta, search, theme. */
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  import SearchButton from './SearchButton.vue'
  import ThemeToggle from './ThemeToggle.vue'

  const route = useRoute()
  const title = computed(() => (route.meta.title as string | undefined) ?? 'Gene Curator')
</script>

<style scoped>
  .header-title {
    font-weight: 600;
    margin: 0;
  }
</style>
