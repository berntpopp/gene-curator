<template>
  <v-bottom-navigation v-if="isAuthenticated && authReady" grow tag="nav" aria-label="Primary">
    <v-btn
      v-for="item in tabs"
      :key="item.name"
      :to="item.to"
      :aria-label="item.badge ? `${item.label}, ${item.badge} pending` : item.label"
    >
      <v-badge v-if="item.badge" :content="item.badge" color="warning">
        <v-icon>{{ item.icon }}</v-icon>
      </v-badge>
      <v-icon v-else>{{ item.icon }}</v-icon>
      <span>{{ item.tabLabel }}</span>
    </v-btn>

    <v-menu location="top">
      <template #activator="{ props }">
        <v-btn v-bind="props" aria-label="Account">
          <v-icon>mdi-account</v-icon>
          <span>Account</span>
        </v-btn>
      </template>
      <v-list>
        <BaseNavigationItem :to="{ name: 'UserProfile' }" icon="mdi-account" label="Profile" />
        <BaseNavigationItem
          v-for="item in admin"
          :key="item.name"
          :to="item.to"
          :icon="item.icon"
          :label="item.label"
        />
        <BaseNavigationItem icon="mdi-logout" label="Logout" @click="handleLogout" />
      </v-list>
    </v-menu>
  </v-bottom-navigation>
</template>

<script setup lang="ts">
  /** Phone navigation (below md, signed in). Entries come from useNavEntries (route meta). */
  import BaseNavigationItem from './BaseNavigationItem.vue'
  import { computed } from 'vue'
  import { useLogout } from './useLogout'
  import { useNavEntries } from './useNavEntries'

  const { primary, admin, isAuthenticated, authReady } = useNavEntries()
  // Phone.png puts Genes before Scopes; tabOrder overrides the rail order
  const tabs = computed(() => [...primary.value].sort((a, b) => a.tabOrder - b.tabOrder))

  const handleLogout = useLogout()
</script>
