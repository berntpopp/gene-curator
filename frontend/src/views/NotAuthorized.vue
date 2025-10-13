<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" md="6" class="text-center">
        <v-icon color="warning" size="120" class="mb-4"> mdi-lock-alert </v-icon>
        <h1 class="text-h3 mb-4">Access Denied</h1>
        <p class="text-h6 mb-6 text-medium-emphasis">
          You don't have permission to access this page.
        </p>
        <div class="d-flex justify-center gap-3">
          <v-btn :to="{ name: 'Home' }" color="primary"> Go Home </v-btn>
          <v-btn :to="{ name: 'Genes' }" color="secondary"> Browse Genes </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  // Static error page
</script>

<style scoped>
  .fill-height {
    min-height: 70vh;
  }

  .gap-3 {
    gap: 1rem;
  }
</style>
