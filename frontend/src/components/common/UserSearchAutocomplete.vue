<!--
  UserSearchAutocomplete Component

  Reusable autocomplete component for searching users within a scope.
  Designed for GitHub-style member invitation workflow.

  **Features**:
  - Debounced search (300ms)
  - Shows user avatar, name, email
  - Excludes users already members of scope
  - Loading state during search

  **Props**:
  - scopeId: Required scope UUID for searching non-members
  - modelValue: v-model for selected user
  - placeholder: Custom placeholder text
  - excludeUserIds: Additional user IDs to exclude

  @example
  <UserSearchAutocomplete
    v-model="selectedUser"
    :scope-id="scopeId"
    placeholder="Search for a user..."
    @update:model-value="handleUserSelected"
  />
-->

<template>
  <v-autocomplete
    v-model="internalValue"
    :items="searchResults"
    :loading="searching"
    :search="searchQuery"
    item-title="displayName"
    item-value="id"
    :label="label"
    :placeholder="placeholder"
    return-object
    clearable
    hide-no-data
    no-filter
    variant="outlined"
    density="comfortable"
    @update:search="onSearchUpdate"
  >
    <!-- Custom item template -->
    <template #item="{ item, props }">
      <v-list-item v-bind="props" :title="undefined" :subtitle="undefined">
        <template #prepend>
          <v-avatar size="36" color="primary">
            <span class="text-caption font-weight-bold">
              {{ getInitials(item.raw.name) }}
            </span>
          </v-avatar>
        </template>

        <v-list-item-title class="font-weight-medium">
          {{ item.raw.name || item.raw.email }}
        </v-list-item-title>

        <v-list-item-subtitle>
          <span>{{ item.raw.email }}</span>
          <span v-if="item.raw.institution" class="ml-2 text-caption">
            ({{ item.raw.institution }})
          </span>
        </v-list-item-subtitle>
      </v-list-item>
    </template>

    <!-- Selected item display -->
    <template #selection="{ item }">
      <v-chip
        v-if="item.raw"
        color="primary"
        variant="tonal"
        closable
        @click:close="clearSelection"
      >
        <v-avatar start size="24" color="primary">
          <span class="text-caption">{{ getInitials(item.raw.name) }}</span>
        </v-avatar>
        {{ item.raw.name || item.raw.email }}
      </v-chip>
    </template>

    <!-- Loading indicator -->
    <template #append-inner>
      <v-progress-circular v-if="searching" indeterminate size="20" width="2" />
    </template>

    <!-- No results message -->
    <template #no-data>
      <v-list-item v-if="searchQuery && searchQuery.length >= 2 && !searching">
        <v-list-item-title class="text-medium-emphasis">
          No users found matching "{{ searchQuery }}"
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-else-if="searchQuery && searchQuery.length < 2">
        <v-list-item-title class="text-medium-emphasis">
          Type at least 2 characters to search
        </v-list-item-title>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

<script setup>
  import { ref, watch, computed } from 'vue'
  import { scopeService } from '@/services/scopeService'
  import { useLogger } from '@/composables/useLogger'

  // ============================================
  // PROPS & EMITS
  // ============================================

  const props = defineProps({
    /**
     * Scope ID for searching non-members
     */
    scopeId: {
      type: String,
      required: true
    },
    /**
     * v-model value (selected user object)
     */
    modelValue: {
      type: Object,
      default: null
    },
    /**
     * Input label
     */
    label: {
      type: String,
      default: 'Search users'
    },
    /**
     * Placeholder text
     */
    placeholder: {
      type: String,
      default: 'Type to search by name, email, or institution...'
    },
    /**
     * Additional user IDs to exclude from results
     */
    excludeUserIds: {
      type: Array,
      default: () => []
    }
  })

  const emit = defineEmits(['update:modelValue'])

  // ============================================
  // COMPOSABLES
  // ============================================

  const logger = useLogger()

  // ============================================
  // STATE
  // ============================================

  const searchQuery = ref('')
  const searchResults = ref([])
  const searching = ref(false)
  const debounceTimeout = ref(null)

  // ============================================
  // COMPUTED
  // ============================================

  const internalValue = computed({
    get: () => props.modelValue,
    set: value => emit('update:modelValue', value)
  })

  // ============================================
  // METHODS
  // ============================================

  /**
   * Get user initials for avatar
   */
  const getInitials = name => {
    if (!name) return '?'
    const parts = name.trim().split(' ')
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
  }

  /**
   * Clear current selection
   */
  const clearSelection = () => {
    internalValue.value = null
    searchQuery.value = ''
    searchResults.value = []
  }

  /**
   * Handle search input changes with debouncing
   */
  const onSearchUpdate = query => {
    searchQuery.value = query

    // Clear previous timeout
    if (debounceTimeout.value) {
      clearTimeout(debounceTimeout.value)
    }

    // Don't search if query is too short
    if (!query || query.length < 2) {
      searchResults.value = []
      searching.value = false
      return
    }

    // Debounce search
    debounceTimeout.value = setTimeout(() => {
      performSearch(query)
    }, 300)
  }

  /**
   * Perform the actual search
   */
  const performSearch = async query => {
    searching.value = true

    try {
      const results = await scopeService.searchUsersForInvite(props.scopeId, query)

      // Filter out excluded users
      let filtered = results
      if (props.excludeUserIds.length > 0) {
        filtered = results.filter(user => !props.excludeUserIds.includes(user.id))
      }

      // Add display name for autocomplete
      searchResults.value = filtered.map(user => ({
        ...user,
        displayName: user.name || user.email
      }))

      logger.debug('User search completed', {
        query,
        resultCount: searchResults.value.length
      })
    } catch (error) {
      logger.error('User search failed', {
        query,
        error: error.message,
        stack: error.stack
      })
      searchResults.value = []
    } finally {
      searching.value = false
    }
  }

  // ============================================
  // WATCHERS
  // ============================================

  // Clear results when scope changes
  watch(
    () => props.scopeId,
    () => {
      searchResults.value = []
      searchQuery.value = ''
    }
  )
</script>

<style scoped>
  .v-autocomplete :deep(.v-field__input) {
    min-height: 48px;
  }
</style>
