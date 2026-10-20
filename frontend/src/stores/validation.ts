import { defineStore } from 'pinia'
import { errorMessage } from './apiError'
import { validationAPI } from '@/api'
import type { Schema } from '@/types/api'
import type { JsonSchemaDocument } from '@/components/dynamic/types'

/** A field type descriptor: the endpoint's dict entry plus its key as `name`. */
export type FieldTypeInfo = Record<string, unknown> & { name: string }

/** A business rule descriptor: the endpoint's dict entry plus its key as `name`. */
export type BusinessRule = Record<string, unknown> & { name: string }

/** The backend answers with `{ <name>: {...descriptor} }`; the store keeps a list. */
function namedList(dict: Record<string, Record<string, unknown>>) {
  return Object.entries(dict).map(([name, info]) => ({ ...info, name }))
}

interface ValidationState {
  supportedFieldTypes: FieldTypeInfo[]
  businessRules: BusinessRule[]
  validationResults: Record<string, Schema<'ValidationResponse'>>
  jsonSchemas: Record<string, JsonSchemaDocument>
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
        const result = await validationAPI.validateEvidence(validationData)

        this.validationResults[key] = result
        return result
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async validateSchema(schemaDefinition: Record<string, unknown>) {
      this.loading = true
      this.error = null
      try {
        const result = await validationAPI.validateSchema({
          schema_definition: schemaDefinition
        })

        return result
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async generateJsonSchema(schemaId: string) {
      this.loading = true
      this.error = null
      try {
        // The endpoint wraps the document: {json_schema, field_count, ...}
        const response = await validationAPI.generateJsonSchema(schemaId)
        const jsonSchema = response.json_schema as JsonSchemaDocument

        this.jsonSchemas[schemaId] = jsonSchema
        return jsonSchema
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
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
        const fieldTypes = namedList(await validationAPI.getSupportedFieldTypes())
        this.supportedFieldTypes = fieldTypes
        return fieldTypes
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async fetchBusinessRules() {
      if (this.businessRules.length > 0) {
        return this.businessRules
      }

      try {
        const rules = namedList(await validationAPI.getBusinessRules())
        this.businessRules = rules
        return rules
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    async validateField(fieldData: Schema<'FieldValidationRequest'>) {
      try {
        const result = await validationAPI.validateField(fieldData)

        return result
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
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
