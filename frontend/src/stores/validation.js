import { defineStore } from 'pinia'
import { validationAPI } from '@/api'

export const useValidationStore = defineStore('validation', {
  state: () => ({
    supportedFieldTypes: [],
    businessRules: [],
    validationResults: {},
    jsonSchemas: {},
    loading: false,
    error: null
  }),

  getters: {
    getValidationResult: state => key => {
      return state.validationResults[key]
    },

    getJsonSchema: state => schemaId => {
      return state.jsonSchemas[schemaId]
    },

    getSupportedFieldType: state => typeName => {
      return state.supportedFieldTypes.find(type => type.name === typeName)
    }
  },

  actions: {
    async validateEvidence(evidenceData, schemaId, key = 'default') {
      this.loading = true
      this.error = null
      try {
        const validationData = {
          evidence_data: evidenceData,
          schema_id: schemaId
        }
        const result = await validationAPI.validateEvidence(validationData)
        this.validationResults[key] = result
        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async validateSchema(schemaDefinition) {
      this.loading = true
      this.error = null
      try {
        const result = await validationAPI.validateSchema({
          schema_definition: schemaDefinition
        })
        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async generateJsonSchema(schemaId) {
      this.loading = true
      this.error = null
      try {
        const jsonSchema = await validationAPI.generateJsonSchema(schemaId)
        this.jsonSchemas[schemaId] = jsonSchema
        return jsonSchema
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSupportedFieldTypes() {
      if (this.supportedFieldTypes.length > 0) {
        return this.supportedFieldTypes
      }

      try {
        const fieldTypes = await validationAPI.getSupportedFieldTypes()
        this.supportedFieldTypes = fieldTypes
        return fieldTypes
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchBusinessRules() {
      if (this.businessRules.length > 0) {
        return this.businessRules
      }

      try {
        const rules = await validationAPI.getBusinessRules()
        this.businessRules = rules
        return rules
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async validateField(fieldData) {
      try {
        const result = await validationAPI.validateField(fieldData)
        return result
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    clearValidationResult(key) {
      if (this.validationResults[key]) {
        delete this.validationResults[key]
      }
    },

    clearAllValidationResults() {
      this.validationResults = {}
    },

    clearError() {
      this.error = null
    }
  }
})
