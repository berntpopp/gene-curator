<template>
  <v-container class="py-12 text-center">
    <v-img
      src="/img/logo.png"
      alt="Gene Curator Logo"
      width="88"
      aspect-ratio="1"
      class="mx-auto mb-6"
    />
    <h1 class="text-headline-large mb-3">Gene Curator</h1>
    <p class="text-body-large text-medium-emphasis mx-auto mb-6" style="max-width: 36rem">
      Methodology-agnostic platform for clinical genetics teams to curate gene-disease associations
      using ClinGen, GenCC, or custom frameworks.
    </p>
    <div class="d-flex justify-center ga-4 flex-wrap">
      <v-btn :to="{ name: 'GeneCatalogue' }" color="primary" size="large">Browse genes</v-btn>
      <v-btn v-if="!authStore.isAuthenticated" :to="{ name: 'Login' }" size="large">
        {{ TERMINOLOGY.SIGN_IN }}
      </v-btn>
    </div>
  </v-container>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { useAuthStore } from '@/stores/auth'

  const authStore = useAuthStore()
</script>
