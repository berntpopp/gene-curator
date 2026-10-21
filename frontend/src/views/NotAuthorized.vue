<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" md="6" class="text-center">
        <v-icon color="warning" size="96" class="mb-4"> mdi-lock-alert </v-icon>
        <h1 class="text-h4 mb-4">Access Denied</h1>
        <p class="text-body-1 mb-6 text-medium-emphasis">
          This page needs an administrator account.
        </p>
        <div class="d-flex justify-center align-center ga-4">
          <v-btn v-if="!authStore.isAuthenticated" :to="signInTo" color="primary">Sign in</v-btn>
          <v-btn v-else :to="{ name: 'Dashboard' }" color="primary"> Go to dashboard </v-btn>
          <v-btn :to="{ name: 'Home' }" variant="text"> Go home </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useRoute } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'

  const route = useRoute()
  const authStore = useAuthStore()
  // The router guard passes the blocked path along so sign-in can return there
  const signInTo = computed(() => ({ name: 'Login', query: { redirect: route.query.redirect } }))
</script>

<style scoped>
  .fill-height {
    min-height: 70vh;
  }
</style>
