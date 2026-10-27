<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <div class="text-center mb-6">
          <v-img
            src="/img/logo.png"
            alt="Gene Curator Logo"
            width="88"
            aspect-ratio="1"
            class="mx-auto mb-4"
          />
          <h1 class="text-headline-small mb-1">Sign in to Gene Curator</h1>
          <p class="text-body-medium text-medium-emphasis">
            Gene-disease validity curation with second-curator review.
          </p>
        </div>

        <v-card class="pa-6" variant="flat" border>
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
                role="alert"
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
                variant="outlined"
                :rules="emailRules"
                validate-on="blur"
                autocomplete="username"
                autofocus
                required
                class="mb-3"
              />

              <v-text-field
                v-model="credentials.password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="passwordRules"
                validate-on="blur"
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
            </v-form>
          </v-card-text>
        </v-card>

        <div class="text-center text-body-medium mt-4">
          <p class="mb-1">
            No account?
            <router-link :to="{ name: 'Register' }"
              >Ask your scope admin for an invitation</router-link
            >
          </p>
          <p>
            Just looking?
            <router-link :to="{ name: 'GeneCatalogue' }">Browse curated genes</router-link>
          </p>
        </div>

        <p class="text-center text-body-small text-medium-emphasis mt-4">
          Research use only. Not for clinical decision-making.
        </p>

        <!-- Development Login Helper -->
        <v-card v-if="isDevelopment" class="mt-4 pa-4" variant="tonal" color="info">
          <v-card-title class="text-body-large"> Development quick login </v-card-title>
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
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, reactive, nextTick } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'
  import { safeRedirect } from '@/utils/safeRedirect'

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

  // Plain build-time constant (not computed) so production builds drop devCredentials (#461)
  const isDevelopment =
    import.meta.env.DEV ||
    import.meta.env.MODE === 'development' ||
    import.meta.env.VITE_ENABLE_DEV_LOGIN === 'true'

  // Validation rules
  const emailRules = [
    (v: string) => !!v || 'Email is required',
    (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const passwordRules = [(v: string) => !!v || 'Password is required']

  // Development quick login credentials
  // Note: admin is application-level, others are standard users with scope-specific roles
  type DevRole = 'admin' | 'curator' | 'reviewer' | 'viewer'
  const devCredentials: Record<DevRole, { email: string; password: string }> | null = isDevelopment
    ? {
        admin: { email: 'admin@genecurator.org', password: 'admin123' }, // Application admin
        curator: { email: 'alice.smith@genecurator.org', password: 'admin123' }, // User (curator role in kidney-genetics scope)
        reviewer: { email: 'bob.jones@genecurator.org', password: 'admin123' }, // User (reviewer role in cardio-genetics scope)
        viewer: { email: 'carol.williams@genecurator.org', password: 'admin123' } // User (viewer role in neuro-genetics scope)
      }
    : null

  const handleLogin = async () => {
    const result = await loginForm.value?.validate()
    if (result && !(result as { valid: boolean }).valid) return

    try {
      authStore.clearError()

      await authStore.login(credentials)

      // Redirect to intended page or home
      router.push(safeRedirect(route.query.redirect) ?? { name: 'Home' })
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
    const creds = devCredentials?.[role]
    if (!creds) return

    // Fill credentials
    credentials.email = creds.email
    credentials.password = creds.password
    await nextTick() // let the inputs pick up the values before validate()

    await handleLogin()
  }
</script>
