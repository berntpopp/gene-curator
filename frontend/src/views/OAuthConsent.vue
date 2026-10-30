<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card :loading="loading">
          <v-card-title class="text-title-large">Connect an MCP client</v-card-title>
          <v-card-text>
            <v-alert v-if="error" type="error" data-test="consent-error">{{ error }}</v-alert>
            <template v-else-if="request">
              <p class="text-body-large mb-4">
                <strong>{{ request.client_name }}</strong> wants to act as you in Gene Curator, with
                exactly your permissions{{ readOnly ? ', read-only' : '' }}.
              </p>
              <p class="text-body-medium mb-2">After you decide, you are sent to:</p>
              <p class="mb-4">
                <code data-test="consent-redirect">{{ request.redirect_uri }}</code>
              </p>
              <p class="text-body-medium text-medium-emphasis">
                Only allow clients you started yourself. The connection appears under Access tokens,
                where you can revoke it at any time.
              </p>
            </template>
          </v-card-text>
          <v-card-actions v-if="request && !error">
            <v-spacer />
            <v-btn :disabled="deciding" data-test="consent-deny" @click="decide(false)">
              Deny
            </v-btn>
            <v-btn
              color="primary"
              variant="flat"
              :loading="deciding"
              data-test="consent-allow"
              @click="decide(true)"
            >
              Allow
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute } from 'vue-router'
  import apiClient from '@/api/client'
  import { errorMessage } from '@/stores/apiError'
  import type { Schema } from '@/types/api'

  const route = useRoute()
  const id = String(route.query.request ?? '')
  const request = ref<Schema<'OAuthAuthorizationRequest'> | null>(null)
  const error = ref('')
  const loading = ref(true)
  const deciding = ref(false)
  const readOnly = computed(() => !request.value?.scopes.includes('write'))
  const url = `/oauth/authorizations/${encodeURIComponent(id)}`

  onMounted(async () => {
    try {
      request.value = (await apiClient.get<Schema<'OAuthAuthorizationRequest'>>(url)).data
    } catch (err) {
      error.value = errorMessage(err, 'This authorization request is not valid')
    } finally {
      loading.value = false
    }
  })

  async function decide(approve: boolean): Promise<void> {
    deciding.value = true
    try {
      const body: Schema<'OAuthConsent'> = { approve }
      const { data } = await apiClient.post<Schema<'OAuthConsentRedirect'>>(url, body)
      // The server only issues HTTPS or loopback redirect URIs (checked at registration)
      window.location.assign(data.redirect_url)
    } catch (err) {
      error.value = errorMessage(err, 'Could not complete the authorization')
      deciding.value = false
    }
  }
</script>
