<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Gene Assignments</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Manage gene-disease curation assignments and workload distribution
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="flat" to="/scope-selection" size="large">
        <v-icon start>mdi-plus</v-icon>
        New Assignment
      </v-btn>
    </div>

    <!-- Assignment Manager Component -->
    <GeneAssignmentManager />
  </v-container>
</template>

<script setup>
  import GeneAssignmentManager from '@/components/dynamic/GeneAssignmentManager.vue'
</script>
