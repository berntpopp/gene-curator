<template>
  <v-footer color="surface" class="footer-bar">
    <v-container class="py-1">
      <v-row align="center" justify="center" dense>
        <v-col cols="12" md="6" class="text-center text-md-left">
          <span class="text-body-small"> © {{ currentYear }} Gene Curator - Halbritter Lab </span>
        </v-col>
        <v-col cols="12" md="6" class="text-center text-md-right">
          <v-btn
            v-for="link in footerLinks"
            :key="link.name"
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            variant="text"
            size="small"
            class="text-body-small"
          >
            <v-icon start size="small">{{ link.icon }}</v-icon>
            {{ link.title }}
          </v-btn>

          <!-- Disclaimer Button with Acknowledgment Indicator -->
          <v-tooltip location="top">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                variant="text"
                size="small"
                class="text-body-small"
                @click="showDisclaimer"
              >
                <v-icon size="small" class="mr-1">mdi-scale-balance</v-icon>
                Disclaimer
                <v-icon
                  v-if="disclaimerStore.isAcknowledged"
                  size="x-small"
                  color="success"
                  class="ml-1"
                >
                  mdi-check-circle
                </v-icon>
              </v-btn>
            </template>
            <span v-if="disclaimerStore.isAcknowledged">
              Acknowledged on {{ disclaimerStore.formattedAcknowledgmentDate }}
            </span>
            <span v-else>View research use disclaimer</span>
          </v-tooltip>

          <!-- Log Viewer Button with Error Count Badge -->
          <v-btn
            v-if="showLogs"
            variant="text"
            size="small"
            class="text-body-small"
            :title="`Open Log Viewer (Ctrl+Shift+L) - ${logStore.errorCount} errors`"
            @click="logStore.showViewer"
          >
            <v-badge
              :content="logStore.errorCount"
              :model-value="logStore.errorCount > 0"
              color="error"
              overlap
            >
              <v-icon size="small">mdi-text-box-search-outline</v-icon>
            </v-badge>
            <span class="ml-1">Logs</span>
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { useAuthStore } from '@/stores/auth'
  import { useLogStore } from '@/stores/logStore'
  import { useDisclaimerStore } from '@/stores/disclaimer'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  const authStore = useAuthStore()
  const logStore = useLogStore()
  const showLogs = computed(() => import.meta.env.DEV || authStore.isAdmin)
  const disclaimerStore = useDisclaimerStore()
  const currentYear = computed(() => new Date().getFullYear())

  const footerLinks = [
    {
      name: 'github',
      title: 'GitHub',
      url: 'https://github.com/halbritter-lab/gene-curator',
      icon: 'mdi-github'
    },
    {
      name: 'documentation',
      title: 'Docs',
      url: 'https://github.com/halbritter-lab/gene-curator/wiki',
      icon: 'mdi-book-open-variant'
    }
  ]

  const showDisclaimer = () => {
    logger.debug('Disclaimer button clicked in footer')
    disclaimerStore.showDisclaimerDialog()
  }
</script>

<style scoped>
  .v-footer {
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }
</style>
