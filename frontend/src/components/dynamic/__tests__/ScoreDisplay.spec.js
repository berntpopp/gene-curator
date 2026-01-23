import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import ScoreDisplay from '../ScoreDisplay.vue'

// Mock useSchemaScoring composable
vi.mock('@/composables/useSchemaScoring', () => ({
  useSchemaScoring: vi.fn((scores, config) => ({
    totalScore: ref(scores.value?.total_score || 0),
    categoryScores: ref(scores.value || {}),
    classification: ref('Moderate'),
    classificationColor: ref('info'),
    nearThreshold: ref(false),
    progressPercentage: ref(50),
    maxScore: ref(config.value?.max_score || 18)
  }))
}))

// Mock useLogger
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  })
}))

// Vuetify component stubs
const vuetifyStubs = {
  'v-card': {
    template: '<div class="v-card"><slot /></div>'
  },
  'v-card-title': {
    template: '<div class="v-card-title"><slot /></div>'
  },
  'v-card-text': {
    template: '<div class="v-card-text"><slot /></div>'
  },
  'v-icon': {
    template: '<span class="v-icon"><slot /></span>',
    props: ['icon', 'start', 'color', 'size']
  },
  'v-chip': {
    template: '<span class="v-chip" :data-color="color"><slot /></span>',
    props: ['color', 'size', 'variant']
  },
  'v-skeleton-loader': {
    template: '<div class="v-skeleton-loader" />',
    props: ['type']
  },
  'v-progress-linear': {
    template: '<div class="v-progress-linear" :data-value="modelValue"><slot /></div>',
    props: ['modelValue', 'color', 'height', 'rounded']
  },
  'v-alert': {
    template: '<div class="v-alert" v-if="modelValue !== false"><slot /></div>',
    props: ['type', 'variant', 'density', 'icon', 'modelValue']
  },
  'v-expansion-panels': {
    template: '<div class="v-expansion-panels"><slot /></div>'
  },
  'v-expansion-panel': {
    template: '<div class="v-expansion-panel"><slot /></div>'
  },
  'v-expansion-panel-title': {
    template: '<div class="v-expansion-panel-title"><slot /></div>'
  },
  'v-expansion-panel-text': {
    template: '<div class="v-expansion-panel-text"><slot /></div>'
  },
  'v-row': {
    template: '<div class="v-row"><slot /></div>'
  },
  'v-col': {
    template: '<div class="v-col"><slot /></div>',
    props: ['cols']
  }
}

describe('ScoreDisplay', () => {
  const defaultProps = {
    scoreCalculations: {
      genetic_evidence_score: 6,
      experimental_evidence_score: 3,
      total_score: 9
    },
    scoringConfiguration: {
      engine: 'clingen',
      max_score: 18,
      classification_thresholds: {
        Definitive: 12,
        Strong: 7,
        Moderate: 2,
        Limited: 0.1
      }
    },
    loading: false
  }

  function createWrapper(props = {}) {
    return mount(ScoreDisplay, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: vuetifyStubs
      }
    })
  }

  describe('loading state', () => {
    it('shows skeleton loader when loading', () => {
      const wrapper = createWrapper({ loading: true })
      expect(wrapper.find('.v-skeleton-loader').exists()).toBe(true)
    })

    it('hides skeleton loader when not loading', () => {
      const wrapper = createWrapper({ loading: false })
      expect(wrapper.find('.v-skeleton-loader').exists()).toBe(false)
    })
  })

  describe('score display', () => {
    it('renders card with Live Scoring title', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.v-card-title').text()).toContain('Live Scoring')
    })

    it('displays classification chip', () => {
      const wrapper = createWrapper()
      const chip = wrapper.find('.v-chip')
      expect(chip.exists()).toBe(true)
    })

    it('shows progress bar', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.v-progress-linear').exists()).toBe(true)
    })
  })

  describe('classification colors', () => {
    it('uses info color for Moderate classification', () => {
      const wrapper = createWrapper()
      const chip = wrapper.find('.v-chip')
      expect(chip.attributes('data-color')).toBe('info')
    })
  })

  describe('threshold panel', () => {
    it('renders expansion panel for thresholds', () => {
      const wrapper = createWrapper()
      expect(wrapper.find('.v-expansion-panels').exists()).toBe(true)
    })
  })

  describe('null handling', () => {
    it('handles null scoreCalculations gracefully', () => {
      const wrapper = createWrapper({ scoreCalculations: null })
      expect(wrapper.exists()).toBe(true)
    })

    it('handles null scoringConfiguration gracefully', () => {
      const wrapper = createWrapper({ scoringConfiguration: null })
      expect(wrapper.exists()).toBe(true)
    })
  })
})
