<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="pa-6" elevation="8">
          <v-card-title class="text-center mb-4">
            <v-img
              src="/img/logo.png"
              alt="Gene Curator Logo"
              width="64"
              aspect-ratio="1"
              class="mx-auto mb-4"
            />
            <h1 class="text-h4">{{ TERMINOLOGY.SIGN_IN }}</h1>
          </v-card-title>

          <v-card-text>
            <v-form ref="loginForm" @submit.prevent="handleLogin">
              <v-alert
                v-if="route.query.reason === 'expired'"
                type="info"
                variant="tonal"
                class="mb-4"
              >
                Your session expired. Sign in to continue.
              </v-alert>

              <v-alert
                v-if="authStore.error"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="authStore.clearError"
              >
                {{ authStore.error }}
              </v-alert>

              <v-text-field
                v-model="credentials.email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email"
                variant="outlined"
                :rules="emailRules"
                autocomplete="username"
                autofocus
                required
                class="mb-3"
              />

              <v-text-field
                v-model="credentials.password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="passwordRules"
                autocomplete="current-password"
                required
                class="mb-4"
                @click:append-inner="showPassword = !showPassword"
              />

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="authStore.loading"
                class="mb-4"
              >
                Sign in
              </v-btn>

              <div class="text-center">
                <p class="text-body-2 mb-2">Don't have an account?</p>
                <v-btn :to="{ name: 'Register' }" variant="text" color="primary">
                  Create Account
                </v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- Development Login Helper -->
        <v-card v-if="isDevelopment" class="mt-4 pa-4" variant="tonal" color="info">
          <v-card-title class="text-subtitle-1">
            <v-icon start>mdi-dev-to</v-icon>
            Development Quick Login
          </v-card-title>
          <v-card-text>
            <div class="d-flex flex-column ga-2">
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('admin')"
              >
                Admin
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('curator')"
              >
                Curator (Alice)
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('reviewer')"
              >
                Reviewer (Bob)
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                :loading="authStore.loading"
                @click="quickLogin('viewer')"
              >
                Viewer (Carol)
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { TERMINOLOGY } from '@/config/terminology'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, reactive, computed, nextTick } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'
  import { showSuccess } from '@/composables/useNotifications'

  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()

  // Form state
  const loginForm = ref<{ validate: () => Promise<unknown> } | null>(null)
  const showPassword = ref(false)

  const credentials = reactive({
    email: '',
    password: ''
  })

  // Development mode check
  const isDevelopment = computed(() => {
    return (
      import.meta.env.DEV ||
      import.meta.env.MODE === 'development' ||
      import.meta.env.VITE_ENABLE_DEV_LOGIN === 'true'
    )
  })

  // Validation rules
  const emailRules = [
    (v: string) => !!v || 'Email is required',
    (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const passwordRules = [(v: string) => !!v || 'Password is required']

  // Development quick login credentials
  // Note: admin is application-level, others are standard users with scope-specific roles
  type DevRole = 'admin' | 'curator' | 'reviewer' | 'viewer'
  const devCredentials: Record<DevRole, { email: string; password: string }> = {
    admin: { email: 'admin@genecurator.org', password: 'admin123' }, // Application admin
    curator: { email: 'alice.smith@genecurator.org', password: 'admin123' }, // User (curator role in kidney-genetics scope)
    reviewer: { email: 'bob.jones@genecurator.org', password: 'admin123' }, // User (reviewer role in cardio-genetics scope)
    viewer: { email: 'carol.williams@genecurator.org', password: 'admin123' } // User (viewer role in neuro-genetics scope)
  }

  const handleLogin = async () => {
    const result = await loginForm.value?.validate()
    if (result && !(result as { valid: boolean }).valid) return

    try {
      authStore.clearError()

      await authStore.login(credentials)

      showSuccess('Login successful!')

      // Redirect to intended page or home
      const redirect = route.query.redirect
      const redirectTo = typeof redirect === 'string' && redirect ? redirect : { name: 'Home' }
      router.push(redirectTo)
    } catch (error) {
      const err = error as {
        message?: string
        stack?: string
        response?: { data?: { detail?: string } }
      }
      logger.error('Login error:', { error: err.message, stack: err.stack })
    }
  }

  const quickLogin = async (role: DevRole) => {
    const creds = devCredentials[role]
    if (!creds) return

    // Fill credentials
    credentials.email = creds.email
    credentials.password = creds.password
    await nextTick() // let the inputs pick up the values before validate()

    await handleLogin()
  }
</script>

<style scoped>
  .fill-height {
    background: linear-gradient(
      135deg,
      rgb(var(--v-theme-surface)) 0%,
      rgb(var(--v-theme-background)) 100%
    );
  }

  .v-card {
    backdrop-filter: blur(10px);
    background: rgba(var(--v-theme-surface), 0.9);
  }
</style>
