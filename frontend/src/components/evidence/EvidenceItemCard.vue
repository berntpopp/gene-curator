<template>
  <v-card variant="outlined" class="evidence-card">
    <v-card-text>
      <div class="d-flex justify-space-between align-start">
        <div class="flex-grow-1">
          <!-- Header -->
          <div class="d-flex align-center mb-2">
            <v-chip size="small" :color="getCategoryColor(evidence.evidence_category)">
              {{ formatCategory(evidence.evidence_category) }}
            </v-chip>
            <v-chip
              v-if="evidence.computed_score"
              size="small"
              color="primary"
              variant="outlined"
              class="ml-2"
            >
              {{ evidence.computed_score }} points
            </v-chip>
            <v-spacer />
            <div class="text-caption text-medium-emphasis">#{{ index + 1 }}</div>
          </div>

          <!-- Description -->
          <div class="text-body-2 mb-2">
            {{ evidence.description }}
          </div>

          <!-- PMIDs -->
          <div v-if="evidence.pmids && evidence.pmids.length > 0" class="d-flex flex-wrap gap-1">
            <v-chip
              v-for="pmid in evidence.pmids"
              :key="pmid"
              size="x-small"
              variant="outlined"
              :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`"
              target="_blank"
              class="text-no-wrap"
            >
              <v-icon start size="x-small">mdi-file-document</v-icon>
              PMID:{{ pmid }}
            </v-chip>
          </div>

          <!-- Additional Metadata -->
          <div v-if="evidence.metadata" class="mt-2">
            <div class="text-caption text-medium-emphasis">
              {{ formatMetadata(evidence.metadata) }}
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="ml-3">
          <v-menu>
            <template #activator="{ props: menuProps }">
              <v-btn
                v-bind="menuProps"
                icon
                variant="text"
                size="small"
                aria-label="Evidence actions"
              >
                <v-icon>mdi-dots-vertical</v-icon>
              </v-btn>
            </template>
            <v-list density="compact">
              <v-list-item @click="emit('edit')">
                <template #prepend>
                  <v-icon>mdi-pencil</v-icon>
                </template>
                <v-list-item-title>Edit</v-list-item-title>
              </v-list-item>
              <v-list-item @click="handleDelete">
                <template #prepend>
                  <v-icon color="error">mdi-delete</v-icon>
                </template>
                <v-list-item-title class="text-error">Delete</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
  /**
   * EvidenceItemCard Component
   *
   * Displays a single evidence item with metadata, PMIDs, and action menu.
   * Used in CurationForm's tabbed evidence sections.
   *
   * @example
   * <EvidenceItemCard
   *   :evidence="evidenceItem"
   *   :index="0"
   *   @edit="handleEdit"
   *   @delete="handleDelete"
   * />
   */

  defineProps({
    evidence: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    }
  })

  const emit = defineEmits(['edit', 'delete'])

  /**
   * Get color for evidence category chip
   */
  function getCategoryColor(category) {
    const colorMap = {
      case_level: 'blue',
      segregation: 'purple',
      case_control: 'teal',
      expression: 'orange',
      protein_function: 'pink',
      models: 'cyan',
      rescue: 'lime',
      contradictory: 'red'
    }
    return colorMap[category] || 'grey'
  }

  /**
   * Format category name for display
   */
  function formatCategory(category) {
    return category
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Format metadata object to readable string
   */
  function formatMetadata(metadata) {
    if (!metadata || typeof metadata !== 'object') return ''

    const parts = []
    if (metadata.variant_count) parts.push(`${metadata.variant_count} variants`)
    if (metadata.family_count) parts.push(`${metadata.family_count} families`)
    if (metadata.proband_count) parts.push(`${metadata.proband_count} probands`)

    return parts.join(', ')
  }

  /**
   * Handle delete with confirmation
   */
  function handleDelete() {
    if (confirm('Delete this evidence item?')) {
      emit('delete')
    }
  }
</script>

<style scoped>
  .evidence-card {
    transition: all 0.2s ease;
  }

  .evidence-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .gap-1 {
    gap: 4px;
  }
</style>
