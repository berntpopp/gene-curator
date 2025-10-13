<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-domain</v-icon>
      Select Clinical Scope
    </v-card-title>

    <v-card-text>
      <v-select
        v-model="selectedScope"
        :items="availableScopes"
        :loading="loading"
        item-title="display_name"
        item-value="id"
        label="Clinical Specialty Scope"
        placeholder="Choose your area of expertise..."
        variant="outlined"
        return-object
        @update:model-value="onScopeSelected"
      >
        <template #item="{ props, item }">
          <v-list-item v-bind="props">
            <v-list-item-title>{{ item.raw.display_name }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ item.raw.institution }} • {{ item.raw.description }}
            </v-list-item-subtitle>
            <template #append>
              <v-chip
                :color="item.raw.is_active ? 'success' : 'warning'"
                size="small"
                variant="flat"
              >
                {{ item.raw.is_active ? 'Active' : 'Inactive' }}
              </v-chip>
            </template>
          </v-list-item>
        </template>

        <template #selection="{ item }">
          <div class="d-flex align-center">
            <v-icon start color="primary">mdi-dna</v-icon>
            <div>
              <div class="font-weight-medium">{{ item.raw.display_name }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.raw.institution }}</div>
            </div>
          </div>
        </template>
      </v-select>

      <v-alert v-if="selectedScope" type="info" variant="tonal" class="mt-4">
        <template #prepend>
          <v-icon>mdi-information</v-icon>
        </template>
        <div class="font-weight-medium mb-1">Working in: {{ selectedScope.display_name }}</div>
        <div class="text-body-2">{{ selectedScope.description }}</div>
        <div class="text-caption mt-2">Institution: {{ selectedScope.institution }}</div>
      </v-alert>
    </v-card-text>

    <v-card-actions v-if="selectedScope">
      <v-spacer />
      <v-btn color="primary" variant="flat" @click="proceedWithScope">
        <v-icon start>mdi-arrow-right</v-icon>
        Continue with this scope
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, computed, onMounted } from 'vue'
  import { useScopesStore } from '@/stores'

  const emit = defineEmits(['scope-selected'])

  const scopesStore = useScopesStore()
  const selectedScope = ref(null)

  const loading = computed(() => scopesStore.loading)
  const availableScopes = computed(() => scopesStore.scopes.filter(scope => scope.is_active))

  const onScopeSelected = scope => {
    selectedScope.value = scope
    scopesStore.setCurrentScope(scope)
  }

  const proceedWithScope = () => {
    if (selectedScope.value) {
      emit('scope-selected', selectedScope.value)
    }
  }

  onMounted(async () => {
    try {
      await scopesStore.fetchScopes()
    } catch (error) {
      logger.error('Failed to load scopes:', { error: error.message, stack: error.stack })
    }
  })
</script>
