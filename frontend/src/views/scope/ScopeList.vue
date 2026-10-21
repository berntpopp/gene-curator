<!--
  Scope List View

  Table of the scopes the user can see (public scopes and their memberships), with their own
  role per row. Search, sort, page and density live in the URL (useTableUrlState). Any signed-in
  user may create a scope and becomes its admin (route and POST /scopes/ allow it).
-->

<template>
  <v-container fluid>
    <div class="d-flex align-center mb-4">
      <h1 class="page-title text-headline-large">{{ TERMINOLOGY.SCOPES }}</h1>
      <v-spacer />
      <div class="text-right">
        <v-btn color="primary" variant="flat" @click="navigateToCreate">New scope</v-btn>
        <div class="text-body-small text-medium-emphasis mt-1">You become the scope admin.</div>
      </div>
    </div>

    <DataTable
      v-model:search="search"
      v-model:page="page"
      v-model:items-per-page="itemsPerPage"
      v-model:sort-by="sortBy"
      v-model:density="density"
      :headers="headers"
      :items="pageRows"
      :items-length="rows.length"
      :loading="loading"
      :error="scopeStore.error"
      empty-text="No scopes found. Use New scope to create one."
    >
      <template #item.display_name="{ item }">
        <button type="button" class="scope-link" @click="navigateToScope(item.id)">
          {{ item.display_name }}
        </button>
      </template>
    </DataTable>
  </v-container>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { computed, onMounted } from 'vue'
  import { useRouter } from 'vue-router'
  import { useScopesStore } from '@/stores/scopes'
  import { useLogger } from '@/composables/useLogger'
  import { useTableUrlState } from '@/composables/useTableUrlState'
  import DataTable from '@/components/common/DataTable.vue'

  interface ScopeItem {
    id: string
    name: string
    display_name: string
    description?: string | null
    institution?: string | null
    is_active: boolean
    user_role?: string | null
    stats?: { member_count?: number; total_genes?: number } | null
  }

  const router = useRouter()
  const scopeStore = useScopesStore()
  const logger = useLogger()
  const { search, page, itemsPerPage, sortBy, density } = useTableUrlState()

  const headers = [
    { title: 'Scope', key: 'display_name' },
    { title: 'Institution', key: 'institution' },
    { title: 'Your role', key: 'role' },
    { title: 'Genes', key: 'genes', align: 'end' },
    { title: 'Active', key: 'active' },
    { title: 'Members', key: 'members', align: 'end' }
  ]

  const roleLabel = (role?: string | null) =>
    role ? ((TERMINOLOGY as Record<string, string>)[role.toUpperCase()] ?? role) : '–'

  // The store is typed loosely; narrow to the fields shown. Few scopes, so filter, sort and
  // page here instead of on the server.
  const rows = computed(() => {
    const q = search.value.toLowerCase()
    const all = (scopeStore.scopes as ScopeItem[])
      .filter(
        s =>
          !q ||
          [s.display_name, s.name, s.description, s.institution].some(v =>
            v?.toLowerCase().includes(q)
          )
      )
      .map(s => ({
        id: s.id,
        display_name: s.display_name,
        institution: s.institution ?? '',
        role: roleLabel(s.user_role),
        genes: s.stats?.total_genes ?? 0,
        active: s.is_active ? 'Yes' : 'No',
        members: s.stats?.member_count ?? 0
      }))
    const sort = sortBy.value[0] ?? { key: 'display_name', order: 'asc' as const }
    const dir = sort.order === 'desc' ? -1 : 1
    const key = sort.key as keyof (typeof all)[number]
    return all.sort(
      (a, b) => dir * String(a[key]).localeCompare(String(b[key]), undefined, { numeric: true })
    )
  })

  const pageRows = computed(() =>
    rows.value.slice((page.value - 1) * itemsPerPage.value, page.value * itemsPerPage.value)
  )
  const loading = computed(() => scopeStore.loading)

  const navigateToScope = (scopeId: string) => {
    logger.info('Navigating to scope dashboard', { scope_id: scopeId })
    router.push({ name: 'scope-dashboard', params: { scopeId } })
  }

  const navigateToCreate = () => {
    logger.info('Navigating to scope creation')
    router.push({ name: 'scope-create' })
  }

  onMounted(async () => {
    try {
      logger.debug('Fetching all scopes')
      await scopeStore.fetchUserScopes()
      logger.info('Scopes loaded', { count: scopeStore.scopes.length })
    } catch (error) {
      const err = error as Error
      logger.error('Failed to fetch scopes', { error: err.message, stack: err.stack })
    }
  })
</script>

<style scoped>
  .scope-link {
    background: none;
    border: 0;
    padding: 0;
    cursor: pointer;
    color: rgb(var(--v-theme-secondary));
    font-weight: 500;
    text-align: left;
  }

  .scope-link:hover {
    text-decoration: underline;
  }
</style>
