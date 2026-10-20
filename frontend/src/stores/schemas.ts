import { defineStore } from 'pinia'
import { schemasAPI } from '@/api'
import { toApiError, apiData } from './apiError'
import type { Schema } from '@/types/api'

type CurationSchemaRecord = Schema<'CurationSchema'>
type WorkflowPairRecord = Schema<'WorkflowPair'>

interface SchemasState {
  schemas: CurationSchemaRecord[]
  workflowPairs: WorkflowPairRecord[]
  currentSchema: CurationSchemaRecord | null
  currentWorkflowPair: WorkflowPairRecord | null
  schemaUsageStatistics: Record<string, Record<string, unknown>>
  loading: boolean
  error: string | null
}

export const useSchemasStore = defineStore('schemas', {
  state: (): SchemasState => ({
    schemas: [],
    workflowPairs: [],
    currentSchema: null,
    currentWorkflowPair: null,
    schemaUsageStatistics: {},
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
        const response = apiData<{ schemas?: CurationSchemaRecord[] } & Record<string, unknown>>(
          await schemasAPI.getSchemas(params)
        )
        this.schemas = response.schemas || (response as unknown as CurationSchemaRecord[])
        return response
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSchemaById(id: string) {
      this.loading = true
      this.error = null
      try {
        const schema = apiData<CurationSchemaRecord>(await schemasAPI.getSchemaById(id))
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
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async createSchema(schemaData: Schema<'CurationSchemaCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newSchema = apiData<CurationSchemaRecord>(await schemasAPI.createSchema(schemaData))
        this.schemas.push(newSchema)
        return newSchema
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateSchema(id: string, schemaData: Schema<'CurationSchemaUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedSchema = apiData<CurationSchemaRecord>(
          await schemasAPI.updateSchema(id, schemaData)
        )
        const index = this.schemas.findIndex(s => s.id === id)
        if (index !== -1) {
          this.schemas[index] = updatedSchema
        }
        if (this.currentSchema && this.currentSchema.id === id) {
          this.currentSchema = updatedSchema
        }
        return updatedSchema
      } catch (error) {
        this.error = toApiError(error).message ?? null
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
        this.schemas = this.schemas.filter(s => s.id !== id)
        if (this.currentSchema && this.currentSchema.id === id) {
          this.currentSchema = null
        }
        return true
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSchemaUsageStatistics(id: string) {
      try {
        const statistics = apiData<Record<string, unknown>>(
          await schemasAPI.getSchemaUsageStatistics(id)
        )
        this.schemaUsageStatistics[id] = statistics
        return statistics
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      }
    },

    async fetchWorkflowPairs(params: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = apiData<
          { workflow_pairs?: WorkflowPairRecord[] } & Record<string, unknown>
        >(await schemasAPI.getWorkflowPairs(params))
        this.workflowPairs =
          response.workflow_pairs || (response as unknown as WorkflowPairRecord[])
        return response
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async createWorkflowPair(pairData: Schema<'WorkflowPairCreate'>) {
      this.loading = true
      this.error = null
      try {
        const newPair = apiData<WorkflowPairRecord>(await schemasAPI.createWorkflowPair(pairData))
        this.workflowPairs.push(newPair)
        return newPair
      } catch (error) {
        this.error = toApiError(error).message ?? null
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateWorkflowPair(id: string, pairData: Schema<'WorkflowPairUpdate'>) {
      this.loading = true
      this.error = null
      try {
        const updatedPair = apiData<WorkflowPairRecord>(
          await schemasAPI.updateWorkflowPair(id, pairData)
        )
        const index = this.workflowPairs.findIndex(p => p.id === id)
        if (index !== -1) {
          this.workflowPairs[index] = updatedPair
        }
        if (this.currentWorkflowPair && this.currentWorkflowPair.id === id) {
          this.currentWorkflowPair = updatedPair
        }
        return updatedPair
      } catch (error) {
        this.error = toApiError(error).message ?? null
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
        this.error = toApiError(error).message ?? null
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
