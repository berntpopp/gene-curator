import { defineStore } from 'pinia'
import { scopesAPI } from '@/api'

export const useScopesStore = defineStore('scopes', {
  state: () => ({
    scopes: [],
    currentScope: null,
    scopeUsers: {},
    scopeStatistics: {},
    loading: false,
    error: null
  }),

  getters: {
    getScopeById: state => id => {
      return state.scopes.find(scope => scope.id === id)
    },

    getScopesByInstitution: state => institution => {
      return state.scopes.filter(scope => scope.institution === institution)
    },

    getActiveScopesCount: state => {
      return state.scopes.filter(scope => scope.is_active).length
    }
  },

  actions: {
    async fetchScopes(params = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await scopesAPI.getScopes(params)
        this.scopes = response.scopes || response
        return response
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchScopeById(id) {
      this.loading = true
      this.error = null
      try {
        const scope = await scopesAPI.getScopeById(id)
        this.currentScope = scope

        // Update the scope in the list if it exists
        const index = this.scopes.findIndex(s => s.id === id)
        if (index !== -1) {
          this.scopes[index] = scope
        } else {
          this.scopes.push(scope)
        }

        return scope
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async createScope(scopeData) {
      this.loading = true
      this.error = null
      try {
        const newScope = await scopesAPI.createScope(scopeData)
        this.scopes.push(newScope)
        return newScope
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async updateScope(id, scopeData) {
      this.loading = true
      this.error = null
      try {
        const updatedScope = await scopesAPI.updateScope(id, scopeData)
        const index = this.scopes.findIndex(s => s.id === id)
        if (index !== -1) {
          this.scopes[index] = updatedScope
        }
        if (this.currentScope && this.currentScope.id === id) {
          this.currentScope = updatedScope
        }
        return updatedScope
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteScope(id) {
      this.loading = true
      this.error = null
      try {
        await scopesAPI.deleteScope(id)
        this.scopes = this.scopes.filter(s => s.id !== id)
        if (this.currentScope && this.currentScope.id === id) {
          this.currentScope = null
        }
        return true
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchScopeStatistics(id) {
      try {
        const statistics = await scopesAPI.getScopeStatistics(id)
        this.scopeStatistics[id] = statistics
        return statistics
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async fetchScopeUsers(id) {
      try {
        const users = await scopesAPI.getScopeUsers(id)
        this.scopeUsers[id] = users
        return users
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async assignUserToScope(scopeId, userId, roleData) {
      try {
        const result = await scopesAPI.assignUserToScope(scopeId, userId, roleData)
        // Refresh scope users
        await this.fetchScopeUsers(scopeId)
        return result
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    async removeUserFromScope(scopeId, userId) {
      try {
        const result = await scopesAPI.removeUserFromScope(scopeId, userId)
        // Refresh scope users
        await this.fetchScopeUsers(scopeId)
        return result
      } catch (error) {
        this.error = error.message
        throw error
      }
    },

    setCurrentScope(scope) {
      this.currentScope = scope
    },

    clearCurrentScope() {
      this.currentScope = null
    },

    clearError() {
      this.error = null
    }
  }
})
