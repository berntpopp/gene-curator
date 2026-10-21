<template>
  <div>
    <!-- Hero Section -->
    <v-container fluid class="hero-section pa-8">
      <v-row align="center" justify="center">
        <v-col cols="12" md="8" class="text-center">
          <v-img src="/img/logo.png" alt="Gene Curator Logo" max-width="120" class="mx-auto mb-6" />
          <h1 class="text-h3 mb-4 font-weight-bold">Gene Curator</h1>
          <p class="text-h6 mb-6 text-medium-emphasis">
            Advanced platform for genetic information curation and management with ClinGen
            compliance
          </p>
          <div class="d-flex justify-center ga-4 flex-wrap">
            <v-btn
              :to="{ name: 'GeneCatalogue' }"
              color="primary"
              size="large"
              prepend-icon="mdi-dna"
            >
              Browse Genes
            </v-btn>
            <v-btn
              v-if="!authStore.isAuthenticated"
              :to="{ name: 'Login' }"
              color="secondary"
              size="large"
              prepend-icon="mdi-login"
            >
              {{ TERMINOLOGY.SIGN_IN }}
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </v-container>

    <!-- Statistics Section -->
    <v-container class="py-8">
      <v-row v-if="statistics">
        <v-col cols="12" class="text-center mb-6">
          <h2 class="text-h4 mb-2">Curation Overview</h2>
          <p class="text-subtitle-1 text-medium-emphasis">
            Current state of gene curations across all scopes
          </p>
        </v-col>

        <v-col v-for="stat in statisticsCards" :key="stat.title" cols="12" md="3">
          <v-card class="pa-4 text-center">
            <v-icon :color="stat.color" size="48" class="mb-3">
              {{ stat.icon }}
            </v-icon>
            <div class="text-h4 font-weight-bold mb-1">
              {{ stat.value }}
            </div>
            <div class="text-subtitle-1 text-medium-emphasis">
              {{ stat.title }}
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- Loading state -->
      <v-row v-else>
        <v-col cols="12" class="text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="mt-4 text-subtitle-1">Loading statistics...</p>
        </v-col>
      </v-row>
    </v-container>

    <!-- Features Section -->
    <v-container class="py-8">
      <v-row>
        <v-col cols="12" class="text-center mb-6">
          <h2 class="text-h4 mb-2">Key Features</h2>
          <p class="text-subtitle-1 text-medium-emphasis">
            Comprehensive tools for genetic data management
          </p>
        </v-col>

        <v-col v-for="feature in features" :key="feature.title" cols="12" md="4">
          <v-card class="pa-6 h-100">
            <v-card-text class="text-center">
              <v-icon :color="feature.color" size="64" class="mb-4">
                {{ feature.icon }}
              </v-icon>
              <h3 class="text-h6 mb-3">{{ feature.title }}</h3>
              <p class="text-body-2 text-medium-emphasis">
                {{ feature.description }}
              </p>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, onMounted, computed } from 'vue'
  import { useAuthStore } from '@/stores/auth'
  import { useGenesStore } from '@/stores/genes'
  import type { Schema } from '@/types/api'

  const authStore = useAuthStore()
  const genesStore = useGenesStore()

  const statistics = ref<Schema<'GeneStatistics'> | null>(null)

  const features = [
    {
      title: 'ClinGen Compliance',
      description:
        'Built-in support for ClinGen Standard Operating Procedures v11 with automated evidence scoring',
      icon: 'mdi-certificate',
      color: 'success'
    },
    {
      title: 'Advanced Search',
      description:
        'Powerful search capabilities across gene symbols, HGNC IDs, and dyadic names for efficient curation',
      icon: 'mdi-magnify',
      color: 'info'
    },
    {
      title: 'Data Management',
      description:
        'Comprehensive CRUD operations with bulk import/export capabilities and change tracking',
      icon: 'mdi-database',
      color: 'primary'
    },
    {
      title: 'Role-Based Access',
      description:
        'Secure authentication with granular role-based permissions for viewers, curators, and administrators',
      icon: 'mdi-account-group',
      color: 'warning'
    },
    {
      title: 'Scientific Integrity',
      description:
        'Immutable change logs and cryptographic content addressing for audit trails and provenance',
      icon: 'mdi-shield-check',
      color: 'success'
    },
    {
      title: 'Modern Architecture',
      description:
        'Three-tier architecture with PostgreSQL, FastAPI, and Vue 3 for performance and scalability',
      icon: 'mdi-layers-outline',
      color: 'purple'
    }
  ]

  const statisticsCards = computed(() => {
    if (!statistics.value) return []

    return [
      {
        title: 'Curated Genes',
        value: statistics.value.curated_genes || 0,
        icon: 'mdi-dna',
        color: 'primary'
      },
      {
        title: 'Active Curations',
        value: statistics.value.active_curations || 0,
        icon: 'mdi-clipboard-check',
        color: 'success'
      },
      {
        title: TERMINOLOGY.SCOPES,
        value: statistics.value.total_scopes || 0,
        icon: 'mdi-folder-multiple',
        color: 'info'
      },
      {
        title: 'Pending Review',
        value: statistics.value.pending_review || 0,
        icon: 'mdi-clock-outline',
        color: 'warning'
      }
    ]
  })

  onMounted(async () => {
    try {
      statistics.value = await genesStore.fetchStatistics()
    } catch (error) {
      const err = error as Error
      logger.warn('Failed to load statistics:', { error: err.message, stack: err.stack })
    }
  })
</script>

<style scoped>
  .hero-section {
    background: linear-gradient(
      135deg,
      rgb(var(--v-theme-primary)) 0%,
      rgb(var(--v-theme-secondary)) 100%
    );
    color: white;
    min-height: 400px;
    display: flex;
    align-items: center;
  }

  .v-card {
    transition:
      transform 0.2s ease,
      box-shadow 0.2s ease;
  }

  .v-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
  }
</style>
