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
          <h1 class="text-headline-small mb-1">Create account</h1>
        </div>

        <v-card class="pa-6" variant="flat" border>
          <v-card-text>
            <v-form ref="registerForm" @submit.prevent="handleRegister">
              <v-text-field
                v-model="userData.name"
                label="Full name"
                prepend-inner-icon="mdi-account"
                variant="outlined"
                :rules="nameRules"
                autocomplete="name"
                required
                class="mb-3"
              />

              <v-text-field
                v-model="userData.email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email"
                variant="outlined"
                :rules="emailRules"
                autocomplete="email"
                required
                class="mb-3"
              />

              <v-text-field
                v-model="userData.password"
                label="Password"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="passwordRules"
                autocomplete="new-password"
                required
                class="mb-3"
                @click:append-inner="showPassword = !showPassword"
              />

              <v-text-field
                v-model="confirmPassword"
                label="Confirm Password"
                :type="showConfirmPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock-check"
                :append-inner-icon="showConfirmPassword ? 'mdi-eye' : 'mdi-eye-off'"
                variant="outlined"
                :rules="confirmPasswordRules"
                autocomplete="new-password"
                required
                class="mb-4"
                @click:append-inner="showConfirmPassword = !showConfirmPassword"
              />

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

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="authStore.loading"
                class="mb-4"
              >
                Create account
              </v-btn>

              <div class="text-center">
                <p class="text-body-medium mb-2">Already have an account?</p>
                <v-btn :to="{ name: 'Login' }" variant="text" color="primary"> Sign in </v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth'
  import { passwordRules } from '@/config/password'
  import { showSuccess, showError } from '@/composables/useNotifications'

  const router = useRouter()
  const authStore = useAuthStore()

  // Form state
  const registerForm = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const showPassword = ref(false)
  const showConfirmPassword = ref(false)
  const confirmPassword = ref('')

  // The API requires a name; public sign-up always creates a plain "user" (the server enforces it)
  const userData = reactive({
    name: '',
    email: '',
    password: '',
    role: 'user' as const,
    is_active: true
  })

  const nameRules = [(v: string) => !!v?.trim() || 'Name is required']

  // Validation rules
  const emailRules = [
    (v: string) => !!v || 'Email is required',
    (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const confirmPasswordRules = [
    (v: string) => !!v || 'Please confirm your password',
    (v: string) => v === userData.password || 'Passwords do not match'
  ]

  const handleRegister = async () => {
    const result = await registerForm.value?.validate()
    if (result && !result.valid) return

    try {
      authStore.clearError()

      await authStore.register(userData)

      showSuccess('Account created')
      router.push({ name: 'Home' })
    } catch (error) {
      const err = error as Error
      logger.error('Registration error:', { error: err.message, stack: err.stack })
      showError('Registration failed. Please try again.')
    }
  }
</script>
