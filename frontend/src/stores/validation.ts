import { defineStore } from 'pinia'
import { toApiError, apiData } from './apiError'
import { validationAPI } from '@/api'
import type { Schema } from '@/types/api'

/** A field type descriptor from GET /validation/field-types (fields the store reads). */
export interface FieldTypeInfo {
  name: string
  [key: string]: unknown
}

/** A business rule descriptor (opaque to the store). */
export type BusinessRule = Record<string, unknown>

interface ValidationState {
  supportedFieldTypes: FieldTypeInfo[]
  businessRules: BusinessRule[]
  validationResults: Record<string, Schema<'ValidationResult'>>
  jsonSchemas: Record<string, Schema<'JSONSchemaResponse'>>
  loading: boolean
  error: string | null
}

export const useValidationStore = defineStore('validation', {
  state: (): ValidationState => ({
    supportedFieldTypes: [],
    businessRules: [],
    validationResults: {},
    jsonSchemas: {},
    loading: false,
    error: null
  }),

  getters: {
    getValidationResult: state => (key: string) => {
      return state.validationResults[key]
    },

    getJsonSchema: state => (schemaId: string) => {
      return state.jsonSchemas[schemaId]
    },

    getSupportedFieldType: state => (typeName: string) => {
      return state.supportedFieldTypes.find(type => type.name === typeName)
    }
  },

  actions: {
    async validateEvidence(
      evidenceData: Record<string, unknown>,
      schemaId: string,
      key: string = 'default'
    ) {
      this.loading = true
      this.error = null
      try {
        const validationData = {
          evidence_data: evidenceData,
          schema_id: schemaId
        }
        const result = apiData<Schema<'ValidationResult'>>(
          await validationAPI.validateEvidence(validationData)
        )
        this.validationResults[key] = result
        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async validateSchema(schemaDefinition: Record<string, unknown>) {
      this.loading = true
      this.error = null
      try {
        const result = apiData<Schema<'SchemaValidationResult'>>(
          await validationAPI.validateSchema({
            schema_definition: schemaDefinition
          })
        )
        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async generateJsonSchema(schemaId: string) {
      this.loading = true
      this.error = null
      try {
        const jsonSchema = apiData<Schema<'JSONSchemaResponse'>>(
          await validationAPI.generateJsonSchema(schemaId)
        )
        this.jsonSchemas[schemaId] = jsonSchema
        return jsonSchema
      } catch (error) {
        this.error = toApiError(error).message ?? null
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
        const fieldTypes = apiData<FieldTypeInfo[]>(await validationAPI.getSupportedFieldTypes())
        this.supportedFieldTypes = fieldTypes
        return fieldTypes
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchBusinessRules() {
      if (this.businessRules.length > 0) {
        return this.businessRules
      }

      try {
        const rules = apiData<BusinessRule[]>(await validationAPI.getBusinessRules())
        this.businessRules = rules
        return rules
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async validateField(fieldData: Schema<'FieldValidationRequest'>) {
      try {
        const result = apiData<Schema<'FieldValidationResponse'>>(
          await validationAPI.validateField(fieldData)
        )
        return result
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    clearValidationResult(key: string) {
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
