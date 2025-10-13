/**
 * Disclaimer store
 * Manages disclaimer acknowledgment state using Pinia and persists to localStorage
 *
 * Stores when a user has acknowledged the disclaimer popup, ensuring it only
 * appears once per browser/device. Provides timestamp tracking for audit purposes.
 */

import { defineStore } from 'pinia'
import { logService } from '@/services/logService'

// Storage keys for localStorage persistence
const DISCLAIMER_KEY = 'geneCuratorDisclaimerAcknowledged'
const DISCLAIMER_TIMESTAMP_KEY = 'geneCuratorDisclaimerTimestamp'
const DISCLAIMER_VERSION_KEY = 'geneCuratorDisclaimerVersion'

// Current disclaimer version - increment when disclaimer content changes significantly
const CURRENT_DISCLAIMER_VERSION = '1.0.0'

export const useDisclaimerStore = defineStore('disclaimer', {
  state: () => ({
    isAcknowledged: false,
    acknowledgmentTimestamp: null,
    disclaimerVersion: null,
    showManually: false // Flag to trigger manual display of disclaimer
  }),

  getters: {
    /**
     * Get the formatted acknowledgment date
     * @returns {string} Formatted date string (e.g., "Jan 15, 2025") or empty string
     */
    formattedAcknowledgmentDate: (state) => {
      if (!state.acknowledgmentTimestamp) {
        return ''
      }

      try {
        const date = new Date(state.acknowledgmentTimestamp)
        return date.toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (error) {
        logService.error('Error formatting acknowledgment date', { error: error.message })
        return ''
      }
    },

    /**
     * Check if the current disclaimer version has been acknowledged
     * @returns {boolean} True if current version acknowledged, false otherwise
     */
    isCurrentVersionAcknowledged: (state) => {
      return state.isAcknowledged && state.disclaimerVersion === CURRENT_DISCLAIMER_VERSION
    },

    /**
     * Check if disclaimer should be shown
     * @returns {boolean} True if disclaimer should be shown, false otherwise
     */
    shouldShowDisclaimer: (state) => {
      return !state.isAcknowledged || state.disclaimerVersion !== CURRENT_DISCLAIMER_VERSION
    }
  },

  actions: {
    /**
     * Initialize the store by loading saved acknowledgment from localStorage
     * Should be called once at app startup
     */
    initialize() {
      try {
        const savedAcknowledgment = localStorage.getItem(DISCLAIMER_KEY)
        const savedTimestamp = localStorage.getItem(DISCLAIMER_TIMESTAMP_KEY)
        const savedVersion = localStorage.getItem(DISCLAIMER_VERSION_KEY)

        this.isAcknowledged = savedAcknowledgment === 'true'
        this.acknowledgmentTimestamp = savedTimestamp ? parseInt(savedTimestamp) : null
        this.disclaimerVersion = savedVersion || null

        logService.debug('Disclaimer store initialized', {
          isAcknowledged: this.isAcknowledged,
          version: this.disclaimerVersion,
          currentVersion: CURRENT_DISCLAIMER_VERSION
        })

        // If version mismatch, reset acknowledgment
        if (this.isAcknowledged && this.disclaimerVersion !== CURRENT_DISCLAIMER_VERSION) {
          logService.info('Disclaimer version mismatch, will show updated disclaimer', {
            oldVersion: this.disclaimerVersion,
            newVersion: CURRENT_DISCLAIMER_VERSION
          })
        }
      } catch (error) {
        logService.error('Error loading disclaimer status from localStorage', {
          error: error.message,
          stack: error.stack
        })
        // Default to not acknowledged if there's an error
        this.isAcknowledged = false
        this.acknowledgmentTimestamp = null
        this.disclaimerVersion = null
      }
    },

    /**
     * Save disclaimer acknowledgment to localStorage
     * Stores timestamp, version, and acknowledgment status
     */
    saveAcknowledgment() {
      try {
        const now = Date.now()
        localStorage.setItem(DISCLAIMER_KEY, 'true')
        localStorage.setItem(DISCLAIMER_TIMESTAMP_KEY, now.toString())
        localStorage.setItem(DISCLAIMER_VERSION_KEY, CURRENT_DISCLAIMER_VERSION)

        this.isAcknowledged = true
        this.acknowledgmentTimestamp = now
        this.disclaimerVersion = CURRENT_DISCLAIMER_VERSION

        logService.info('Disclaimer acknowledged and saved', {
          timestamp: now,
          version: CURRENT_DISCLAIMER_VERSION,
          formattedDate: this.formattedAcknowledgmentDate
        })
      } catch (error) {
        logService.error('Error saving disclaimer acknowledgment', {
          error: error.message,
          stack: error.stack
        })
      }
    },

    /**
     * Reset disclaimer acknowledgment (for testing or policy updates)
     * Clears all stored acknowledgment data
     */
    resetAcknowledgment() {
      try {
        localStorage.removeItem(DISCLAIMER_KEY)
        localStorage.removeItem(DISCLAIMER_TIMESTAMP_KEY)
        localStorage.removeItem(DISCLAIMER_VERSION_KEY)

        this.isAcknowledged = false
        this.acknowledgmentTimestamp = null
        this.disclaimerVersion = null

        logService.info('Disclaimer acknowledgment reset')
      } catch (error) {
        logService.error('Error resetting disclaimer acknowledgment', {
          error: error.message,
          stack: error.stack
        })
      }
    },

    /**
     * Trigger manual display of disclaimer
     * Sets a flag that App.vue watches to show the disclaimer dialog
     */
    showDisclaimerDialog() {
      logService.debug('Manual disclaimer dialog requested')
      this.showManually = true
    },

    /**
     * Reset the manual show flag
     * Called after the dialog is shown
     */
    resetShowManually() {
      this.showManually = false
    }
  }
})
