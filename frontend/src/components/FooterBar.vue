<template>
  <v-footer class="bg-grey-darken-3" app>
    <v-container>
      <v-row align="center" justify="center">
        <v-col cols="12" md="6" class="text-center text-md-left">
          <span class="text-caption"> © {{ currentYear }} Gene Curator - Halbritter Lab </span>
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
            class="text-caption"
          >
            <v-icon start size="small">{{ link.icon }}</v-icon>
            {{ link.title }}
          </v-btn>

          <!-- Log Viewer Button with Error Count Badge -->
          <v-btn
            variant="text"
            size="small"
            class="text-caption"
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

<script setup>
  import { computed } from 'vue'
  import { useLogStore } from '@/stores/logStore'

  const logStore = useLogStore()
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
</script>

<style scoped>
  .v-footer {
    border-top: 1px solid rgba(255, 255, 255, 0.12);
  }
</style>
