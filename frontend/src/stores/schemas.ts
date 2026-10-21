import { defineStore } from 'pinia'
import { schemasAPI } from '@/api'
import { errorMessage } from './apiError'
import { useValidationStore } from './validation'
import type { Schema } from '@/types/api'

type CurationSchemaRecord = Schema<'CurationSchema'>
type WorkflowPairRecord = Schema<'WorkflowPair'>

/** 1.0.0 -> 1.0.1; a version without a numeric last part gets ".1" appended. */
const bumpPatch = (version: string) =>
  /\.\d+$/.test(version) ? version.replace(/\d+$/, n => String(Number(n) + 1)) : `${version}.1`

interface SchemasState {
  schemas: CurationSchemaRecord[]
  workflowPairs: WorkflowPairRecord[]
  currentSchema: CurationSchemaRecord | null
  currentWorkflowPair: WorkflowPairRecord | null
  loading: boolean
  error: string | null
}

export const useSchemasStore = defineStore('schemas', {
  state: (): SchemasState => ({
    schemas: [],
    workflowPairs: [],
    currentSchema: null,
    currentWorkflowPair: null,
    loading: false,
    error: null
  }),

  getters: {
    getSchemaById: state => (id: string) => {
      return state.schemas.find(schema => schema.id === id)
    },

    getSchemasByType: state => (type: string) => {
      return state.schemas.filter(schema => schema.schema_type === type)
    },

    getPrecurationSchemas: state => {
      return state.schemas.filter(
        schema => schema.schema_type === 'precuration' || schema.schema_type === 'combined'
      )
    },

    getCurationSchemas: state => {
      return state.schemas.filter(
        schema => schema.schema_type === 'curation' || schema.schema_type === 'combined'
      )
    },

    getWorkflowPairById: state => (id: string) => {
      return state.workflowPairs.find(pair => pair.id === id)
    }
  },

  actions: {
    async fetchSchemas(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await schemasAPI.getSchemas(params)

        this.schemas = response
        return response
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSchemaById(id: string) {
      this.loading = true
      this.error = null
      try {
        const schema = await schemasAPI.getSchemaById(id)
        this.currentSchema = schema

        // Update the schema in the list if it exists
        const index = this.schemas.findIndex(s => s.id === id)
        if (index !== -1) {
          this.schemas[index] = schema
        } else {
          this.schemas.push(schema)
        }

        return schema
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async createSchema(schemaData: Schema<'CurationSchemaCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newSchema = await schemasAPI.createSchema(schemaData)
        this.schemas.push(newSchema)
        return newSchema
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateSchema(id: string, schemaData: Schema<'CurationSchemaUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedSchema = await schemasAPI.updateSchema(id, schemaData)
        delete useValidationStore().jsonSchemas[id] // cached JSON schema is stale now

        const index = this.schemas.findIndex(s => s.id === id)
        if (index !== -1) {
          this.schemas[index] = updatedSchema
        }
        if (this.currentSchema && this.currentSchema.id === id) {
          this.currentSchema = updatedSchema
        }
        return updatedSchema
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteSchema(id: string) {
      this.loading = true
      this.error = null
      try {
        await schemasAPI.deleteSchema(id)
        delete useValidationStore().jsonSchemas[id]
        this.schemas = this.schemas.filter(s => s.id !== id)
        if (this.currentSchema && this.currentSchema.id === id) {
          this.currentSchema = null
        }
        return true
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    /** Validate a stored schema server-side (POST /schemas/curation-schemas/{id}/validate). */
    async validateSchema(id: string) {
      try {
        return await schemasAPI.validateCurationSchema(id)
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      }
    },

    /**
     * Derive an inactive copy (patch version bumped) from the schema's latest published
     * version; the copy's v1 records where it came from. The admin activates it after editing.
     */
    async duplicateSchema(id: string) {
      const source = await schemasAPI.getSchemaById(id)
      const [latest] = await schemasAPI.getVersions(id)
      if (!latest) throw new Error('Schema has no published version')
      const derived = await schemasAPI.deriveSchema(id, latest.id, {
        name: source.name,
        version: bumpPatch(source.version)
      })
      this.schemas.push(derived)
      return derived
    },

    /**
     * The definition a record renders and validates with: its pinned version, or for a new
     * record the schema's latest (what the backend pins on create).
     */
    async fetchPinnedVersion(versionId: string | null | undefined, schemaId: string) {
      if (versionId) return await schemasAPI.getMethodologyVersion(versionId)
      const [latest] = await schemasAPI.getVersions(schemaId)
      if (!latest) throw new Error('Schema has no published version')
      return latest
    },

    async fetchWorkflowPairs(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await schemasAPI.getWorkflowPairs(params)
        this.workflowPairs = response
        return response
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async createWorkflowPair(pairData: Schema<'WorkflowPairCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newPair = await schemasAPI.createWorkflowPair(pairData)
        this.workflowPairs.push(newPair)
        return newPair
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateWorkflowPair(id: string, pairData: Schema<'WorkflowPairUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedPair = await schemasAPI.updateWorkflowPair(id, pairData)

        const index = this.workflowPairs.findIndex(p => p.id === id)
        if (index !== -1) {
          this.workflowPairs[index] = updatedPair
        }
        if (this.currentWorkflowPair && this.currentWorkflowPair.id === id) {
          this.currentWorkflowPair = updatedPair
        }
        return updatedPair
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteWorkflowPair(id: string) {
      this.loading = true
      this.error = null
      try {
        await schemasAPI.deleteWorkflowPair(id)
        this.workflowPairs = this.workflowPairs.filter(p => p.id !== id)
        if (this.currentWorkflowPair && this.currentWorkflowPair.id === id) {
          this.currentWorkflowPair = null
        }
        return true
      } catch (error) {
        this.error = errorMessage(error, 'Request failed')
        throw error
      } finally {
        this.loading = false
      }
    },

    setCurrentSchema(schema: CurationSchemaRecord | null) {
      this.currentSchema = schema
    },

    setCurrentWorkflowPair(pair: WorkflowPairRecord | null) {
      this.currentWorkflowPair = pair
    },

    clearCurrentSchema() {
      this.currentSchema = null
    },

    clearError() {
      this.error = null
    }
  }
})
