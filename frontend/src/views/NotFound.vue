<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" md="6" class="text-center">
        <v-icon color="medium-emphasis" size="96" class="mb-4"> mdi-file-question </v-icon>
        <h1 class="text-h4 mb-4">Page Not Found</h1>
        <p class="text-body-1 mb-6 text-medium-emphasis">
          Nothing exists at <code>{{ route.fullPath }}</code
          >.
        </p>
        <div class="d-flex justify-center align-center ga-4">
          <v-btn :to="{ name: 'Home' }" color="primary"> Go home </v-btn>
          <v-btn :to="{ name: 'GeneCatalogue' }" variant="text"> Gene catalogue </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { useRoute } from 'vue-router'

  const route = useRoute()
</script>

<style scoped>
  .fill-height {
    min-height: 70vh;
  }
</style>
