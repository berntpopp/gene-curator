<template>
  <v-container fluid class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="pa-6" elevation="8">
          <v-card-title class="text-center mb-4">
            <v-img
              src="/img/logo.png"
              alt="Gene Curator Logo"
              max-width="64"
              class="mx-auto mb-4"
            />
            <h2 class="text-h4">Create Account</h2>
          </v-card-title>

          <v-card-text>
            <v-form ref="registerForm" v-model="formValid" @submit.prevent="handleRegister">
              <v-text-field
                v-model="userData.email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email"
                variant="outlined"
                :rules="emailRules"
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
                :disabled="!formValid"
                class="mb-4"
              >
                Create Account
              </v-btn>

              <div class="text-center">
                <p class="text-body-2 mb-2">Already have an account?</p>
                <v-btn :to="{ name: 'Login' }" variant="text" color="primary"> Sign In </v-btn>
              </div>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  import { ref, reactive } from 'vue'
  import { useRouter } from 'vue-router'
  import { useAuthStore } from '@/stores/auth.js'
  import { showSuccess, showError } from '@/composables/useNotifications.js'

  const router = useRouter()
  const authStore = useAuthStore()

  // Form state
  const registerForm = ref(null)
  const formValid = ref(false)
  const showPassword = ref(false)
  const showConfirmPassword = ref(false)
  const confirmPassword = ref('')

  const userData = reactive({
    email: '',
    password: ''
  })

  // Validation rules
  const emailRules = [
    v => !!v || 'Email is required',
    v => /.+@.+\..+/.test(v) || 'Email must be valid'
  ]

  const passwordRules = [
    v => !!v || 'Password is required',
    v => v.length >= 6 || 'Password must be at least 6 characters',
    v => /(?=.*[a-z])/.test(v) || 'Password must contain at least one lowercase letter',
    v => /(?=.*[A-Z])/.test(v) || 'Password must contain at least one uppercase letter',
    v => /(?=.*\d)/.test(v) || 'Password must contain at least one number'
  ]

  const confirmPasswordRules = [
    v => !!v || 'Please confirm your password',
    v => v === userData.password || 'Passwords do not match'
  ]

  const handleRegister = async () => {
    if (!formValid.value) return

    try {
      authStore.clearError()

      await authStore.register(userData)

      showSuccess('Account created successfully! You are now logged in.')
      router.push({ name: 'Home' })
    } catch (error) {
      logger.error('Registration error:', { error: error.message, stack: error.stack })
      showError('Registration failed. Please try again.')
    }
  }
</script>

<style scoped>
  .fill-height {
    min-height: 100vh;
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
