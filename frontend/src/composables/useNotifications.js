import { reactive } from 'vue'

// Global snackbar state management
export const snackbarState = reactive({
  show: false,
  message: '',
  color: 'info',
  timeout: 5000
})

export const showSnackbar = (message, color = 'info', timeout = 5000) => {
  snackbarState.message = message
  snackbarState.color = color
  snackbarState.timeout = timeout
  snackbarState.show = true
}

export const showSuccess = (message, timeout = 5000) => {
  showSnackbar(message, 'success', timeout)
}

export const showError = (message, timeout = 8000) => {
  showSnackbar(message, 'error', timeout)
}

export const showWarning = (message, timeout = 6000) => {
  showSnackbar(message, 'warning', timeout)
}

export const showInfo = (message, timeout = 5000) => {
  showSnackbar(message, 'info', timeout)
}

export const useNotifications = () => {
  return {
    snackbarState,
    showSnackbar,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}
