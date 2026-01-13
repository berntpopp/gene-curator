<template>
  <div class="evidence-data-table">
    <v-table v-if="items.length > 0" density="compact" class="rounded">
      <thead>
        <tr class="bg-grey-lighten-4">
          <th v-for="col in columns" :key="col.key" :style="{ width: col.width }">
            {{ col.label }}
          </th>
          <th v-if="!readonly" style="width: 60px">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in items" :key="index">
          <td v-for="col in columns" :key="col.key">
            <!-- PMID field with link -->
            <template v-if="col.type === 'pmid'">
              <div class="d-flex align-center">
                <v-text-field
                  :model-value="item[col.key]"
                  density="compact"
                  variant="plain"
                  hide-details
                  :readonly="readonly"
                  placeholder="PMID"
                  @update:model-value="updateField(index, col.key, $event)"
                />
                <v-btn
                  v-if="item[col.key]"
                  icon
                  size="x-small"
                  variant="text"
                  :href="`https://pubmed.ncbi.nlm.nih.gov/${item[col.key]}`"
                  target="_blank"
                  title="Open in PubMed"
                >
                  <v-icon size="small">mdi-open-in-new</v-icon>
                </v-btn>
              </div>
            </template>

            <!-- Select field -->
            <template v-else-if="col.type === 'select'">
              <v-select
                :model-value="item[col.key]"
                :items="col.options"
                item-title="label"
                item-value="value"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, col.key, $event)"
              />
            </template>

            <!-- Number field -->
            <template v-else-if="col.type === 'number'">
              <v-text-field
                :model-value="item[col.key]"
                type="number"
                :min="col.min"
                :max="col.max"
                :step="col.step || 1"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, col.key, parseFloat($event) || 0)"
              />
            </template>

            <!-- Default text field -->
            <template v-else>
              <v-text-field
                :model-value="item[col.key]"
                density="compact"
                variant="plain"
                hide-details
                :readonly="readonly"
                @update:model-value="updateField(index, col.key, $event)"
              />
            </template>
          </td>

          <!-- Actions column -->
          <td v-if="!readonly">
            <v-btn icon size="small" color="error" variant="text" @click="$emit('remove', index)">
              <v-icon size="small">mdi-delete</v-icon>
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <!-- Empty state -->
    <v-alert v-else type="info" variant="tonal" density="compact">
      No evidence items added yet. Click "Add Evidence" to begin.
    </v-alert>
  </div>
</template>

<script setup>
  /**
   * EvidenceDataTable
   *
   * Reusable table component for entering ClinGen evidence data.
   * Supports various field types: text, number, select, pmid.
   */

  const props = defineProps({
    items: {
      type: Array,
      default: () => []
    },
    columns: {
      type: Array,
      required: true
    },
    readonly: {
      type: Boolean,
      default: false
    },
    evidenceType: {
      type: String,
      default: ''
    }
  })

  const emit = defineEmits(['update:items', 'remove'])

  function updateField(index, key, value) {
    const newItems = [...props.items]
    newItems[index] = { ...newItems[index], [key]: value }
    emit('update:items', newItems)
  }
</script>

<style scoped>
  .evidence-data-table {
    overflow-x: auto;
  }

  .evidence-data-table :deep(.v-text-field input) {
    font-size: 0.875rem;
  }

  .evidence-data-table :deep(.v-select .v-field__input) {
    font-size: 0.875rem;
  }

  .evidence-data-table :deep(td) {
    padding: 4px 8px !important;
    vertical-align: middle;
  }

  .evidence-data-table :deep(th) {
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
</style>
