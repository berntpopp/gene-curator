<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">
        <h1 class="text-headline-large mb-2">Access tokens</h1>
        <p class="text-body-medium text-medium-emphasis mb-6">
          Personal access tokens let MCP clients and scripts act as you, with exactly your
          permissions. Treat them like passwords and revoke any token you no longer use.
        </p>

        <v-card class="mb-6">
          <v-card-title class="text-title-large">New token</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="create">
              <v-row>
                <v-col cols="12" md="5">
                  <v-text-field
                    v-model="name"
                    label="Name"
                    hint="For example: Claude Code on my laptop"
                    :rules="[(v: string) => !!v.trim() || 'Name is required']"
                    maxlength="100"
                  />
                </v-col>
                <v-col cols="12" md="3">
                  <v-select v-model="days" :items="expiryOptions" label="Expires in" />
                </v-col>
                <v-col cols="12" md="4">
                  <v-checkbox v-model="readOnly" label="Read-only" hide-details />
                </v-col>
              </v-row>
              <v-btn type="submit" color="primary" :loading="creating">Create token</v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <v-card :loading="store.loading">
          <v-card-title class="text-title-large">Your tokens</v-card-title>
          <v-card-text>
            <v-alert v-if="store.error" type="error" class="mb-4">{{ store.error }}</v-alert>
            <v-table v-if="store.tokens.length" density="comfortable">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Token</th>
                  <th scope="col">Access</th>
                  <th scope="col">Expires</th>
                  <th scope="col">Last used</th>
                  <th scope="col"><span class="d-sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in store.tokens" :key="t.id" data-test="token-row">
                  <td>{{ t.name }}</td>
                  <td>
                    <code>{{ t.token_prefix }}…</code>
                  </td>
                  <td>{{ t.scopes.includes('write') ? 'Read and write' : 'Read-only' }}</td>
                  <td>{{ formatDate(t.expires_at) }}</td>
                  <td>{{ t.last_used_at ? formatDateTime(t.last_used_at) : 'Never' }}</td>
                  <td class="text-right">
                    <v-chip v-if="t.revoked_at" size="small">Revoked</v-chip>
                    <v-chip v-else-if="isExpired(t)" size="small">Expired</v-chip>
                    <v-btn
                      v-else
                      size="small"
                      variant="text"
                      color="error"
                      :aria-label="`Revoke ${t.name} (${t.token_prefix}), created ${formatDateTime(t.created_at)}`"
                      @click="revoke(t)"
                    >
                      Revoke
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <p v-else-if="!store.loading" class="text-body-medium text-medium-emphasis">
              You have no tokens yet.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <BaseDialog v-model="showToken" title="Copy your new token" size="md" persistent>
      <p class="mb-4">This is the only time the token is shown. Copy it now and store it safely.</p>
      <v-text-field
        :model-value="plaintext"
        label="Token"
        readonly
        data-test="new-token"
        append-inner-icon="mdi-content-copy"
        @click:append-inner="copy(plaintext)"
      />
      <p class="mb-2">Connect Claude Code with this command:</p>
      <v-text-field
        :model-value="mcpCommand"
        label="Claude Code command"
        readonly
        data-test="mcp-command"
        append-inner-icon="mdi-content-copy"
        @click:append-inner="copy(mcpCommand)"
      />
      <p class="text-body-medium" data-test="mcp-full-hint">
        This connects the curation tools. For administration tools use the same token with
        <code>{{ mcpUrl }}/full</code>.
      </p>
      <template #actions>
        <v-btn color="primary" variant="flat" @click="closeToken">Done</v-btn>
      </template>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useConfirm } from '@/composables/useConfirm'
  import { showError, showSuccess } from '@/composables/useNotifications'
  import { errorMessage } from '@/stores/apiError'
  import { useTokensStore, type PersonalAccessToken } from '@/stores/tokens'
  import { formatDate, formatDateTime } from '@/utils/format'

  const store = useTokensStore()
  const { confirm } = useConfirm()

  const expiryOptions = [7, 30, 90, 365].map(d => ({ title: `${d} days`, value: d }))
  const name = ref('')
  const days = ref(90)
  const readOnly = ref(false)
  const creating = ref(false)
  const plaintext = ref('')
  const showToken = ref(false)

  const mcpUrl = `${import.meta.env.VITE_API_BASE_URL || window.location.origin}/mcp`
  const mcpCommand = computed(
    () =>
      `claude mcp add --transport http gene-curator ${mcpUrl} --header "Authorization: Bearer ${plaintext.value}"`
  )

  // An OAuth connection refreshes its expired hourly token for 30 days: still revocable
  const isExpired = (t: PersonalAccessToken): boolean =>
    !t.name.startsWith('OAuth:') && new Date(t.expires_at) <= new Date()

  async function create(): Promise<void> {
    if (!name.value.trim()) return
    creating.value = true
    try {
      plaintext.value = await store.createToken({
        name: name.value.trim(),
        expires_at: new Date(Date.now() + days.value * 86_400_000).toISOString(),
        scopes: readOnly.value ? ['read'] : ['read', 'write']
      })
      showToken.value = true
      name.value = ''
    } catch (err) {
      showError(errorMessage(err, 'Failed to create token'))
    } finally {
      creating.value = false
    }
  }

  async function copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text)
      showSuccess('Copied')
    } catch {
      showError('Copy failed; select the token and copy it manually')
    }
  }

  function closeToken(): void {
    showToken.value = false
    plaintext.value = ''
  }

  async function revoke(t: PersonalAccessToken): Promise<void> {
    const ok = await confirm({
      title: `Revoke "${t.name}"?`,
      text: 'Clients using this token stop working immediately. This cannot be undone.',
      confirmText: 'Revoke',
      destructive: true
    })
    if (!ok) return
    try {
      await store.revokeToken(t.id)
      showSuccess('Token revoked')
    } catch (err) {
      showError(errorMessage(err, 'Failed to revoke token'))
    }
  }

  onMounted(store.fetchTokens)
</script>
