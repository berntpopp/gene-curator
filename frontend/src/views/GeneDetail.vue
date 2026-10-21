<!--
  GeneDetail View: the gene as a case file.

  Header (symbol, HGNC name, links to external resources), an agreement banner and one assertion
  row per scope (classification, disease, MOI, stage, score, link to the curation), then the HGNC
  record. The summary comes from the gene summary endpoints (full for signed-in users, public
  otherwise); the HGNC lookup never blocks the page.

  @example
  // Route: /genes/:id
-->

<template>
  <v-container>
    <!-- Loading State -->
    <div v-if="loading" class="d-flex flex-column align-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-large text-medium-emphasis mt-6">Loading gene information...</div>
    </div>

    <!-- Error State -->
    <v-alert v-else-if="notFound" type="warning" variant="tonal" class="mb-4">
      <v-alert-title>Gene not found</v-alert-title>
      This gene does not exist or was removed.
      <template #append>
        <v-btn :to="{ name: 'GeneCatalogue' }" variant="text"> Back to the gene catalogue </v-btn>
      </template>
    </v-alert>
    <v-alert v-else-if="error" type="error" variant="tonal" class="mb-4">
      <v-alert-title>Failed to load gene information</v-alert-title>
      {{ error }}
      <template #append>
        <v-btn
          class="retry"
          variant="text"
          color="error"
          @click="loadGene(String(route.params.id))"
        >
          Retry
        </v-btn>
        <v-btn :to="{ name: 'GeneCatalogue' }" variant="text" color="error"> Back to genes </v-btn>
      </template>
    </v-alert>

    <!-- Case file -->
    <template v-else-if="localGene">
      <header class="mb-5">
        <div class="d-flex align-center mb-1">
          <v-btn
            aria-label="Back"
            icon="mdi-arrow-left"
            variant="text"
            size="small"
            class="mr-2"
            @click="goBack"
          />
          <h1 class="text-headline-large font-weight-bold mono">
            {{ hgncData?.symbol || localGene.approved_symbol }}
          </h1>
          <v-chip
            v-if="hgncData?.status && hgncData.status !== 'Approved'"
            size="small"
            variant="outlined"
            class="ml-3"
          >
            {{ hgncData.status }}
          </v-chip>
        </div>
        <p class="text-body-medium text-medium-emphasis mb-2">
          <template v-if="hgncData?.name">{{ hgncData.name }} &middot;</template>
          <span class="mono">{{ hgncData?.hgnc_id || localGene.hgnc_id }}</span>
          <template v-if="band">
            &middot; <span class="mono">{{ band }}</span></template
          >
        </p>
        <nav aria-label="External resources" class="d-flex flex-wrap ga-4">
          <a
            v-for="link in links"
            :key="link.label"
            :href="link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="ext-link"
          >
            {{ link.label }}
          </a>
        </nav>
      </header>

      <v-progress-linear v-if="summaryLoading" indeterminate color="primary" class="mb-4" />
      <v-alert v-else-if="summaryError" type="error" variant="tonal" density="compact" class="mb-4">
        {{ summaryError }}
        <template #append>
          <v-btn variant="text" size="small" @click="loadSummary(localGene.id)">Retry</v-btn>
        </template>
      </v-alert>
      <template v-else-if="scopes.length">
        <AgreementBanner
          class="mb-4"
          :scope-count="scopes.length"
          :has-conflicts="summary?.has_conflicts ?? false"
          :consensus="summary?.consensus_classification"
          :classifications="summary?.classification_summary ?? {}"
        />
        <GeneAssertions class="mb-4" :scopes="scopes" :linked="auth.isAuthenticated" />
      </template>
      <section v-else class="empty mb-4" aria-label="Curations">
        <h2 class="text-title-medium">No curations yet</h2>
        <p class="text-body-medium text-medium-emphasis">
          {{
            auth.isAuthenticated
              ? 'No scope you can see has curated this gene.'
              : 'No public scope has curated this gene.'
          }}
        </p>
      </section>
      <p v-if="hiddenScopes > 0" class="text-body-small text-medium-emphasis mb-4">
        Also curated in {{ hiddenScopes }} {{ hiddenScopes === 1 ? 'scope' : 'scopes' }} you cannot
        see.
      </p>

      <section class="record" aria-labelledby="record-title">
        <h2 id="record-title" class="text-title-medium mb-3">Gene record</h2>
        <dl class="record__grid">
          <div v-for="row in recordRows" :key="row.label">
            <dt>{{ row.label }}</dt>
            <dd :class="{ mono: row.mono }">{{ row.value }}</dd>
          </div>
        </dl>
        <p v-if="auth.isAdmin" class="text-body-small text-medium-emphasis mt-3">
          <span class="mono">{{ localGene.id }}</span> &middot; updated
          {{ formatDateTime(localGene.updated_at) }}
        </p>
      </section>
    </template>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import AgreementBanner from '@/components/gene/casefile/AgreementBanner.vue'
  import GeneAssertions from '@/components/gene/casefile/GeneAssertions.vue'
  import { geneExternalLinks } from '@/components/gene/casefile/externalLinks'
  import { useGenesStore } from '@/stores/genes'
  import { useGeneSummaryStore } from '@/stores/geneSummary'
  import { useAuthStore } from '@/stores/auth'
  import { externalValidationAPI } from '@/api'
  import { useLogger } from '@/composables/useLogger'
  import { EMPTY, formatDateTime } from '@/utils/format'
  import type { Schema } from '@/types/api'

  type Gene = Schema<'Gene'>
  type HgncGene = Schema<'HGNCGeneSearchResult'>

  const route = useRoute()
  const router = useRouter()
  const genesStore = useGenesStore()
  const summaryStore = useGeneSummaryStore()
  const auth = useAuthStore()
  const logger = useLogger()

  const loading = ref(true)
  const error = ref<string | null>(null)
  const notFound = ref(false)
  const hgncData = ref<HgncGene | null>(null)
  const summary = ref<Schema<'GeneSummaryFull'> | Schema<'GeneSummaryPublic'> | null>(null)
  const summaryLoading = ref(false)
  const summaryError = ref<string | null>(null)

  // Local gene data from database (store is JS, so its currentGene is typed null)
  const localGene = computed(() => genesStore.currentGene as Gene | null)

  const aliasSymbols = computed<string[]>(
    () => hgncData.value?.alias_symbols || localGene.value?.alias_symbols || []
  )
  const previousSymbols = computed<string[]>(
    () => hgncData.value?.previous_symbols || localGene.value?.previous_symbols || []
  )
  const band = computed(() => hgncData.value?.location || localGene.value?.location || '')
  const scopes = computed(() => summary.value?.scope_summaries ?? [])
  const hiddenScopes = computed(() => {
    const total = (summary.value as Schema<'GeneSummaryFull'> | null)?.total_scopes_curated ?? 0
    return Math.max(0, total - scopes.value.length)
  })

  const links = computed(() =>
    geneExternalLinks(
      hgncData.value?.symbol || localGene.value?.approved_symbol,
      hgncData.value?.hgnc_id || localGene.value?.hgnc_id
    )
  )

  const recordRows = computed(() => {
    const g = localGene.value
    const list = (xs: string[]) => (xs.length ? xs.join(', ') : EMPTY)
    return [
      { label: 'HGNC ID', value: hgncData.value?.hgnc_id || g?.hgnc_id || EMPTY, mono: true },
      { label: 'Locus type', value: hgncData.value?.locus_type || EMPTY, mono: false },
      {
        label: 'Chromosome',
        value: hgncData.value?.chromosome || g?.chromosome || EMPTY,
        mono: true
      },
      { label: 'Cytogenetic band', value: band.value || EMPTY, mono: true },
      { label: 'Alias symbols', value: list(aliasSymbols.value), mono: true },
      { label: 'Previous symbols', value: list(previousSymbols.value), mono: true }
    ]
  })

  function goBack() {
    if (window.history.state?.back) router.back()
    else router.push({ name: 'GeneCatalogue' })
  }

  /** HGNC enriches the page; it never blocks it, and a failure keeps the local data. */
  async function fetchHgncData(hgncId: string | null | undefined): Promise<void> {
    if (!hgncId) return
    try {
      const response = await externalValidationAPI.fetchHGNCGene(hgncId)
      hgncData.value = response.results[0] ?? null
    } catch (e) {
      logger.warn('Failed to fetch HGNC data, using local data', {
        hgnc_id: hgncId,
        error: (e as Error).message
      })
    }
  }

  async function loadSummary(geneId: string) {
    summaryLoading.value = true
    summaryError.value = null
    try {
      summary.value = await summaryStore.loadSummary(geneId, auth.isAuthenticated)
    } catch (e) {
      summary.value = null
      summaryError.value = 'Could not load the curations for this gene.'
      logger.error('Failed to load gene summary', { gene_id: geneId, error: (e as Error).message })
    } finally {
      summaryLoading.value = false
    }
  }

  async function loadGene(geneId: string) {
    try {
      loading.value = true
      error.value = null
      notFound.value = false
      hgncData.value = null
      summary.value = null

      const gene = await genesStore.fetchGeneById(geneId)
      loading.value = false
      void fetchHgncData(gene.hgnc_id)
      void loadSummary(gene.id)
      logger.info('Gene details loaded', { gene_id: geneId, symbol: gene.approved_symbol })
    } catch (err) {
      const e = err as Error
      logger.error('Failed to load gene details', { error: e.message, stack: e.stack })
      // A malformed id is rejected as 400/422: to the user that is also "not found"
      const status = (err as { response?: { status?: number } }).response?.status
      notFound.value = status === 404 || status === 400 || status === 422
      error.value = 'Failed to load gene details'
    } finally {
      loading.value = false
    }
  }

  // Reload when navigating between genes (the component is reused for /genes/:id)
  watch(() => route.params.id as string, loadGene, { immediate: true })
</script>

<style scoped>
  .ext-link {
    color: rgb(var(--v-theme-info));
    text-decoration: underline;
    text-underline-offset: 2px;
    font-size: 13px;
  }

  .empty,
  .record {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 8px;
    padding: 16px;
  }

  .record__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px 24px;
    margin: 0;
  }

  .record__grid dt {
    font-size: 12px;
    color: rgb(var(--v-theme-on-surface-variant));
  }

  .record__grid dd {
    margin: 0;
    font-size: 13px;
    line-height: 18px;
    overflow-wrap: anywhere;
  }
</style>
