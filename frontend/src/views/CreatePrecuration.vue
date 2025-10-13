<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <PrecurationForm
            :gene-id="geneId"
            @submit="handleSubmit"
            @cancel="handleCancel"
            @saved="handleSaved"
          />
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  import { useRouter, useRoute } from 'vue-router'
  import { showSuccess } from '@/composables/useNotifications.js'
  import PrecurationForm from '@/components/clingen/PrecurationForm.vue'

  const router = useRouter()
  const route = useRoute()

  const geneId = route.query.gene_id || null

  const handleSubmit = precuration => {
    // Navigate to the precuration detail page
    router.push({
      name: 'PrecurationDetail',
      params: { id: precuration.id }
    })
  }

  const handleCancel = () => {
    // Navigate back to precurations list
    router.push({ name: 'Precurations' })
  }

  const handleSaved = () => {
    showSuccess('Pre-curation saved successfully')
  }
</script>
