<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <CurationForm
            :gene-id="geneId"
            :precuration-id="precurationId"
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
  import CurationForm from '@/components/clingen/CurationForm.vue'

  const router = useRouter()
  const route = useRoute()

  const geneId = route.query.gene_id || null
  const precurationId = route.query.precuration_id || null

  const handleSubmit = curation => {
    // Navigate to the curation detail page
    router.push({
      name: 'CurationDetail',
      params: { id: curation.id }
    })
  }

  const handleCancel = () => {
    // Navigate back to curations list
    router.push({ name: 'Curations' })
  }

  const handleSaved = () => {
    showSuccess('Curation saved successfully')
  }
</script>
