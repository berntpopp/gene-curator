/**
 * Component Registry Tests
 *
 * Tests for the dynamic field component registry
 *
 * Test Coverage:
 * - Registry exports verification
 * - Component lookup functionality
 * - Null/undefined handling
 * - Case sensitivity verification
 *
 * @see src/components/dynamic/componentRegistry.js
 */

import { describe, it, expect } from 'vitest'
import { componentRegistry, getComponent } from '../componentRegistry'

describe('componentRegistry', () => {
  describe('Registry Exports', () => {
    it('exports componentRegistry object', () => {
      expect(componentRegistry).toBeDefined()
      expect(typeof componentRegistry).toBe('object')
      expect(componentRegistry).not.toBeNull()
    })

    it('contains all 5 specialized components', () => {
      const expectedComponents = [
        'MONDOAutocomplete',
        'PMIDInput',
        'HPOInheritanceSelect',
        'OMIMAutocomplete',
        'HPOInput'
      ]

      const registryKeys = Object.keys(componentRegistry)

      expectedComponents.forEach(componentName => {
        expect(registryKeys).toContain(componentName)
      })

      expect(registryKeys).toHaveLength(5)
    })

    it('each registered component is a valid Vue component', () => {
      Object.values(componentRegistry).forEach(component => {
        expect(component).toBeDefined()
        // Vue components are objects with a name or __name property
        expect(typeof component).toBe('object')
      })
    })
  })

  describe('getComponent Function', () => {
    it('getComponent returns component for valid name', () => {
      const mondoComponent = getComponent('MONDOAutocomplete')
      expect(mondoComponent).toBe(componentRegistry.MONDOAutocomplete)

      const pmidComponent = getComponent('PMIDInput')
      expect(pmidComponent).toBe(componentRegistry.PMIDInput)

      const hpoInheritanceComponent = getComponent('HPOInheritanceSelect')
      expect(hpoInheritanceComponent).toBe(componentRegistry.HPOInheritanceSelect)

      const omimComponent = getComponent('OMIMAutocomplete')
      expect(omimComponent).toBe(componentRegistry.OMIMAutocomplete)

      const hpoComponent = getComponent('HPOInput')
      expect(hpoComponent).toBe(componentRegistry.HPOInput)
    })

    it('getComponent returns null for unknown name', () => {
      expect(getComponent('UnknownComponent')).toBeNull()
      expect(getComponent('RandomWidget')).toBeNull()
      expect(getComponent('NotAComponent')).toBeNull()
    })

    it('getComponent returns null for empty string', () => {
      expect(getComponent('')).toBeNull()
    })

    it('getComponent returns null for null input', () => {
      expect(getComponent(null)).toBeNull()
    })

    it('getComponent returns null for undefined input', () => {
      expect(getComponent(undefined)).toBeNull()
    })
  })

  describe('Case Sensitivity', () => {
    it('component names are case-sensitive - lowercase fails', () => {
      expect(getComponent('mondoautocomplete')).toBeNull()
      expect(getComponent('pmidinput')).toBeNull()
      expect(getComponent('hpoinheritanceselect')).toBeNull()
    })

    it('component names are case-sensitive - uppercase fails', () => {
      expect(getComponent('MONDOAUTOCOMPLETE')).toBeNull()
      expect(getComponent('PMIDINPUT')).toBeNull()
      expect(getComponent('HPOINPUT')).toBeNull()
    })

    it('component names are case-sensitive - mixed case fails', () => {
      expect(getComponent('MondoAutoComplete')).toBeNull()
      expect(getComponent('Pmidinput')).toBeNull()
      expect(getComponent('hpoInput')).toBeNull()
    })
  })
})
