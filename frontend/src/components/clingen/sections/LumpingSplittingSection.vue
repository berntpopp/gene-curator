<template>
  <div class="lumping-splitting-section">
    <v-alert type="info" variant="tonal" class="mb-4">
      <template #prepend>
        <v-icon>mdi-information</v-icon>
      </template>
      <div class="font-weight-medium">Disease Entity Information</div>
      <div class="text-body-2 mt-1">
        This information is inherited from the approved precuration and is read-only. To modify the
        disease entity definition, update the precuration.
      </div>
    </v-alert>

    <v-card variant="outlined">
      <v-card-title class="text-subtitle-1">
        <v-icon start size="small">mdi-hospital-box</v-icon>
        Disease Entity
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              :model-value="diseaseName"
              label="Disease Name"
              variant="outlined"
              density="compact"
              readonly
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              :model-value="mondoId"
              label="MONDO ID"
              variant="outlined"
              density="compact"
              readonly
              hide-details
            >
              <template #append-inner>
                <v-btn
                  v-if="mondoId"
                  icon
                  size="x-small"
                  variant="text"
                  :href="`https://monarchinitiative.org/disease/${mondoId}`"
                  target="_blank"
                >
                  <v-icon size="small">mdi-open-in-new</v-icon>
                </v-btn>
              </template>
            </v-text-field>
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              :model-value="modeOfInheritance"
              label="Mode of Inheritance"
              variant="outlined"
              density="compact"
              readonly
              hide-details
            />
          </v-col>
        </v-row>

        <!-- Phenotypes -->
        <v-row v-if="phenotypes && phenotypes.length > 0" class="mt-2">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">Associated Phenotypes</div>
            <v-chip-group>
              <v-chip
                v-for="(phenotype, index) in phenotypes"
                :key="index"
                size="small"
                variant="outlined"
              >
                {{ phenotype }}
              </v-chip>
            </v-chip-group>
          </v-col>
        </v-row>

        <!-- Curation Type (per ClinGen Lumping & Splitting guidelines) -->
        <v-row v-if="curationType" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" class="mr-1">mdi-format-list-bulleted-type</v-icon>
              Curation Type
            </div>
            <v-chip :color="getCurationTypeColor(curationType)" variant="tonal" size="large">
              {{ getCurationTypeLabel(curationType) }}
            </v-chip>
          </v-col>
        </v-row>

        <!-- Lumping & Splitting Rationale (multiple choice per ClinGen) -->
        <v-row v-if="rationaleChoices && rationaleChoices.length > 0" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" class="mr-1">mdi-lightbulb-outline</v-icon>
              Rationale Criteria
            </div>
            <v-chip-group>
              <v-chip
                v-for="rationale in rationaleChoices"
                :key="rationale"
                size="small"
                color="secondary"
                variant="tonal"
              >
                {{ getRationaleLabel(rationale) }}
              </v-chip>
            </v-chip-group>
          </v-col>
        </v-row>

        <!-- Evaluation Date -->
        <v-row v-if="evaluationDate" class="mt-2">
          <v-col cols="12" md="4">
            <v-text-field
              :model-value="evaluationDate"
              label="Evaluation Date"
              variant="outlined"
              density="compact"
              readonly
              hide-details
              prepend-inner-icon="mdi-calendar"
            />
          </v-col>
        </v-row>

        <!-- Included MIM Phenotypes -->
        <v-row v-if="includedMimPhenotypes && includedMimPhenotypes.length > 0" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" color="success" class="mr-1">mdi-check-circle</v-icon>
              Included MIM Phenotypes
            </div>
            <v-table density="compact">
              <thead>
                <tr class="bg-success-lighten-5">
                  <th>MIM Number</th>
                  <th>Name</th>
                  <th>Inheritance</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="mim in includedMimPhenotypes" :key="mim.mim_number">
                  <td>
                    <a
                      :href="`https://omim.org/entry/${mim.mim_number}`"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ mim.mim_number }}
                      <v-icon size="x-small">mdi-open-in-new</v-icon>
                    </a>
                  </td>
                  <td>{{ mim.name }}</td>
                  <td>{{ mim.inheritance || '-' }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-col>
        </v-row>

        <!-- Excluded MIM Phenotypes -->
        <v-row v-if="excludedMimPhenotypes && excludedMimPhenotypes.length > 0" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" color="warning" class="mr-1">mdi-close-circle</v-icon>
              Excluded MIM Phenotypes
            </div>
            <v-table density="compact">
              <thead>
                <tr class="bg-warning-lighten-5">
                  <th>MIM Number</th>
                  <th>Name</th>
                  <th>Inheritance</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="mim in excludedMimPhenotypes" :key="mim.mim_number">
                  <td>
                    <a
                      :href="`https://omim.org/entry/${mim.mim_number}`"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {{ mim.mim_number }}
                      <v-icon size="x-small">mdi-open-in-new</v-icon>
                    </a>
                  </td>
                  <td>{{ mim.name }}</td>
                  <td>{{ mim.inheritance || '-' }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-col>
        </v-row>

        <!-- Supporting PMIDs -->
        <v-row v-if="supportingPmids && supportingPmids.length > 0" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" class="mr-1">mdi-book-open-page-variant</v-icon>
              Supporting Literature
            </div>
            <v-chip-group>
              <v-chip
                v-for="pmid in supportingPmids"
                :key="pmid"
                size="small"
                variant="outlined"
                :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}`"
                target="_blank"
              >
                PMID: {{ pmid }}
                <v-icon end size="x-small">mdi-open-in-new</v-icon>
              </v-chip>
            </v-chip-group>
          </v-col>
        </v-row>

        <!-- Rationale Notes -->
        <v-row v-if="rationaleNotes" class="mt-4">
          <v-col cols="12">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" class="mr-1">mdi-note-text</v-icon>
              Rationale Notes
            </div>
            <v-alert type="info" variant="outlined" density="compact">
              {{ rationaleNotes }}
            </v-alert>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Link to Precuration -->
    <v-card v-if="precurationId" variant="text" class="mt-4">
      <v-card-text class="text-center">
        <v-btn
          variant="outlined"
          color="primary"
          :to="{ name: 'precuration-detail', params: { precurationId } }"
        >
          <v-icon start>mdi-file-document</v-icon>
          View Source Precuration
        </v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
  /**
   * LumpingSplittingSection
   *
   * Displays disease entity and lumping/splitting information from the approved precuration.
   * This section is read-only in the curation form per ClinGen SOP v11.
   *
   * Per ClinGen Lumping & Splitting guidelines:
   * - Curation Type: Single choice indicating the type of curation
   * - Rationale: Multiple choice criteria met for the lumping/splitting decision
   * - Included/Excluded MIM Phenotypes
   * - Supporting PMIDs
   */

  import { computed } from 'vue'

  const props = defineProps({
    precurationData: {
      type: Object,
      default: () => ({})
    },
    readonly: {
      type: Boolean,
      default: true
    }
  })

  // ClinGen Curation Type options
  const CURATION_TYPE_OPTIONS = {
    single_from_list: {
      label: 'Curate a single gene-disease entity from this list',
      color: 'primary'
    },
    single_not_on_list: {
      label: 'Curate a single gene-disease entity not on this list',
      color: 'info'
    },
    isolated_phenotype: {
      label: 'Curate an isolated phenotype that is part of this disease entity (Discouraged)',
      color: 'warning'
    },
    lumped_entity: {
      label: 'Curate a "lumped" disease entity from this list',
      color: 'success'
    }
  }

  // ClinGen Rationale options
  const RATIONALE_OPTIONS = {
    assertion: 'Assertion',
    molecular_mechanism: 'Molecular Mechanism',
    phenotypic_variability: 'Phenotypic Variability',
    inheritance_pattern: 'Inheritance Pattern',
    dispute_entity: 'To dispute an asserted entity',
    insufficient_evidence: 'Insufficient evidence to support multiple distinct diseases'
  }

  const diseaseName = computed(
    () =>
      props.precurationData?.disease_name ||
      props.precurationData?.entity_definition?.disease_name ||
      'Not specified'
  )

  const mondoId = computed(
    () =>
      props.precurationData?.mondo_id || props.precurationData?.entity_definition?.mondo_id || null
  )

  const modeOfInheritance = computed(
    () =>
      props.precurationData?.mode_of_inheritance ||
      props.precurationData?.entity_definition?.mode_of_inheritance ||
      'Unknown'
  )

  const phenotypes = computed(
    () =>
      props.precurationData?.phenotypes ||
      props.precurationData?.entity_definition?.phenotypes ||
      []
  )

  // ClinGen Curation Type
  const curationType = computed(
    () =>
      props.precurationData?.curation_type ||
      props.precurationData?.lumping_splitting?.curation_type ||
      null
  )

  // ClinGen Rationale (multiple choice)
  const rationaleChoices = computed(
    () =>
      props.precurationData?.rationale || props.precurationData?.lumping_splitting?.rationale || []
  )

  // Evaluation date
  const evaluationDate = computed(
    () =>
      props.precurationData?.evaluation_date ||
      props.precurationData?.lumping_splitting?.evaluation_date ||
      null
  )

  // Included MIM Phenotypes
  const includedMimPhenotypes = computed(
    () =>
      props.precurationData?.included_mim_phenotypes ||
      props.precurationData?.lumping_splitting?.included_mim_phenotypes ||
      []
  )

  // Excluded MIM Phenotypes
  const excludedMimPhenotypes = computed(
    () =>
      props.precurationData?.excluded_mim_phenotypes ||
      props.precurationData?.lumping_splitting?.excluded_mim_phenotypes ||
      []
  )

  // Supporting PMIDs
  const supportingPmids = computed(() => {
    const pmids =
      props.precurationData?.supporting_pmids ||
      props.precurationData?.lumping_splitting?.supporting_pmids ||
      props.precurationData?.pmids ||
      ''
    // Handle both array and comma-separated string
    if (Array.isArray(pmids)) return pmids
    if (typeof pmids === 'string' && pmids.trim()) {
      return pmids.split(',').map(p => p.trim())
    }
    return []
  })

  // Rationale notes/free text
  const rationaleNotes = computed(
    () =>
      props.precurationData?.rationale_notes ||
      props.precurationData?.lumping_splitting?.notes ||
      props.precurationData?.notes ||
      null
  )

  const precurationId = computed(
    () => props.precurationData?.id || props.precurationData?.precuration_id || null
  )

  // Helper functions
  function getCurationTypeLabel(type) {
    return CURATION_TYPE_OPTIONS[type]?.label || type
  }

  function getCurationTypeColor(type) {
    return CURATION_TYPE_OPTIONS[type]?.color || 'grey'
  }

  function getRationaleLabel(rationale) {
    return RATIONALE_OPTIONS[rationale] || rationale
  }
</script>

<style scoped>
  .lumping-splitting-section :deep(a) {
    text-decoration: none;
    color: rgb(var(--v-theme-primary));
  }

  .lumping-splitting-section :deep(a:hover) {
    text-decoration: underline;
  }
</style>
