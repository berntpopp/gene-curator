<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" md="6" class="text-center">
        <v-icon color="error" size="120" class="mb-4"> mdi-file-question </v-icon>
        <h1 class="text-h3 mb-4">Page Not Found</h1>
        <p class="text-h6 mb-6 text-medium-emphasis">The page you're looking for doesn't exist.</p>
        <div class="d-flex justify-center gap-3">
          <v-btn :to="{ name: 'Home' }" color="primary"> Go Home </v-btn>
          <v-btn :to="{ name: 'Genes' }" color="secondary"> Browse Genes </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  // Static 404 page
</script>

<style scoped>
  .fill-height {
    min-height: 70vh;
  }

  .gap-3 {
    gap: 1rem;
  }
</style>
