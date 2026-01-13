import { defineStore } from 'pinia'
import { schemasAPI } from '@/api'

export const useSchemasStore = defineStore('schemas', {
  state: () => ({
    schemas: [],
    workflowPairs: [],
    currentSchema: null,
    currentWorkflowPair: null,
    schemaUsageStatistics: {},
    loading: false,
    error: null
  }),

  getters: {
    getSchemaById: state => id => {
      return state.schemas.find(schema => schema.id === id)
    },

    getSchemasByType: state => type => {
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

    getWorkflowPairById: state => id => {
      return state.workflowPairs.find(pair => pair.id === id)
    }
  },

  actions: {
    async fetchSchemas(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await schemasAPI.getSchemas(params)
        this.schemas = response.schemas || response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSchemaById(id) {
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
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createSchema(schemaData) {
      this.loading = true
      this.error = null
      try {
        const newSchema = await schemasAPI.createSchema(schemaData)
        this.schemas.push(newSchema)
        return newSchema
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateSchema(id, schemaData) {
      this.loading = true
      this.error = null
      try {
        const updatedSchema = await schemasAPI.updateSchema(id, schemaData)
        const index = this.schemas.findIndex(s => s.id === id)
        if (index !== -1) {
          this.schemas[index] = updatedSchema
        }
        if (this.currentSchema && this.currentSchema.id === id) {
          this.currentSchema = updatedSchema
        }
        return updatedSchema
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteSchema(id) {
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
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchSchemaUsageStatistics(id) {
      try {
        const statistics = await schemasAPI.getSchemaUsageStatistics(id)
        this.schemaUsageStatistics[id] = statistics
        return statistics
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchWorkflowPairs(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await schemasAPI.getWorkflowPairs(params)
        this.workflowPairs = response.workflow_pairs || response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createWorkflowPair(pairData) {
      this.loading = true
      this.error = null
      try {
        const newPair = await schemasAPI.createWorkflowPair(pairData)
        this.workflowPairs.push(newPair)
        return newPair
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteWorkflowPair(id) {
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
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    setCurrentSchema(schema) {
      this.currentSchema = schema
    },

    setCurrentWorkflowPair(pair) {
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
