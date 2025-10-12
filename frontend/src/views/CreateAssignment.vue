<template>
  <v-container fluid>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" class="mr-4" @click="$router.back()" />
      <div>
        <h1 class="text-h4 font-weight-bold">Create New Assignment</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Create a new gene-disease curation assignment
        </p>
      </div>
    </div>

    <!-- Redirect to scope selection flow -->
    <v-card>
      <v-card-text class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64" />
        <div class="mt-4 text-h6">Redirecting to assignment creation flow...</div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
  import { onMounted } from 'vue'
  import { useRouter } from 'vue-router'

  const router = useRouter()

  onMounted(() => {
    // Redirect to the scope selection flow
    router.replace({ name: 'ScopeSelection' })
  })
</script>
