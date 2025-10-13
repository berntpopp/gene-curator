<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">Gene Administration</h1>

        <!-- Action Tabs -->
        <v-tabs v-model="activeTab" class="mb-6">
          <v-tab value="add">Add Gene</v-tab>
          <v-tab value="bulk">Bulk Import</v-tab>
          <v-tab value="manage">Manage Genes</v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- Add Single Gene -->
          <v-window-item value="add">
            <v-card>
              <v-card-title>Add New Gene</v-card-title>
              <v-card-text>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  Add a single gene to the database with all required information.
                </p>
                <div class="text-center pa-8">
                  <v-icon size="64" class="mb-4 text-medium-emphasis">mdi-form-select</v-icon>
                  <h3 class="text-h6 mb-2">Gene Form</h3>
                  <p class="text-body-2 text-medium-emphasis">
                    Coming soon - Individual gene creation and editing form
                  </p>
                </div>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Bulk Import -->
          <v-window-item value="bulk">
            <v-card>
              <v-card-title>Bulk Gene Import</v-card-title>
              <v-card-text>
                <p class="text-body-2 text-medium-emphasis mb-4">
                  Import multiple genes from a CSV file or paste data directly.
                </p>
                <div class="text-center pa-8">
                  <v-icon size="64" class="mb-4 text-medium-emphasis">mdi-file-upload</v-icon>
                  <h3 class="text-h6 mb-2">Bulk Import</h3>
                  <p class="text-body-2 text-medium-emphasis">
                    Coming soon - CSV file upload and bulk gene import
                  </p>
                </div>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- Manage Genes -->
          <v-window-item value="manage">
            <v-card>
              <v-card-title>Manage Existing Genes</v-card-title>
              <v-card-text>
                <div class="text-center pa-8">
                  <v-icon size="64" class="mb-4 text-medium-emphasis">mdi-table-edit</v-icon>
                  <h3 class="text-h6 mb-2">Gene Management</h3>
                  <p class="text-body-2 text-medium-emphasis">
                    Coming soon - Advanced gene management table with editing capabilities
                  </p>
                  <v-divider class="my-4" />
                  <p class="text-body-2">
                    For now, use the
                    <router-link to="/genes" class="text-decoration-none">Genes page</router-link>
                    to browse existing genes.
                  </p>
                </div>
              </v-card-text>
            </v-card>
          </v-window-item>
        </v-window>
      </v-col>
    </v-row>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title>Confirm Deletion</v-card-title>
        <v-card-text>
          Are you sure you want to delete the gene
          <strong>{{ geneToDelete?.approved_symbol }}</strong
          >? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="loading" @click="confirmDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, onMounted } from 'vue'
  import { useRoute } from 'vue-router'
  import { useGenesStore } from '@/stores/genes.js'
  import { showSuccess, showError } from '@/composables/useNotifications.js'

  const route = useRoute()
  const genesStore = useGenesStore()

  const activeTab = ref('add')
  const loading = ref(false)
  const editingGene = ref(null)
  const deleteDialog = ref(false)
  const geneToDelete = ref(null)

  const confirmDelete = async () => {
    try {
      loading.value = true
      await genesStore.deleteGene(geneToDelete.value.id)
      showSuccess('Gene deleted successfully!')
      deleteDialog.value = false
      geneToDelete.value = null
    } catch (error) {
      logger.error('Delete failed:', { error: error.message, stack: error.stack })
      showError('Failed to delete gene. Please try again.')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    // Check if editing from query params
    if (route.query.edit) {
      const geneId = route.query.edit
      const gene = genesStore.getGeneById(geneId)
      if (gene) {
        editingGene.value = gene
        activeTab.value = 'add'
      }
    }
  })
</script>

<style scoped>
  .v-tabs {
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
</style>
