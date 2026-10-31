import { ref } from 'vue'
import { validationAPI } from '@/api'
import { errorMessage } from '@/stores/apiError'
import type { ScoringConfig } from './pointModel'

export interface Diagnostic {
  field: string
  message: string
  severity: 'error' | 'warning'
}

export interface TestResult {
  name: string
  total: unknown
  verdict: unknown
  failures: string[]
}

type Fields = Record<string, unknown> | undefined

/**
 * Server-side checks of an unsaved scoring configuration: the schema validator's
 * diagnostics (POST /validation/validate-schema) and the embedded `tests`, each scored by
 * the real engine (POST /validation/validate-evidence) and compared like publish does
 * (crud/schema_repository.py `_test_failures`).
 */
export function usePointModelChecks() {
  const diagnostics = ref<Diagnostic[]>([])
  const results = ref<TestResult[]>([])
  const checking = ref(false)
  const running = ref(false)
  const error = ref('')

  const definition = (config: ScoringConfig, fields: Fields) => ({
    field_definitions: fields ?? {},
    scoring_configuration: config
  })

  // Replies can land out of order: only the latest check may set the diagnostics
  let run = 0
  async function validate(schema: Record<string, unknown>, prefix = '') {
    const mine = ++run
    checking.value = true
    error.value = ''
    try {
      const r = await validationAPI.validateSchema({ schema_definition: schema })
      if (mine !== run) return
      diagnostics.value = [...r.errors, ...r.warnings]
        .map(d => d as unknown as Diagnostic)
        .filter(d => String(d.field).startsWith(prefix))
    } catch (e) {
      if (mine === run) error.value = errorMessage(e, 'Check failed')
    } finally {
      if (mine === run) checking.value = false
    }
  }

  const check = (config: ScoringConfig, fields?: Fields) =>
    validate(definition(config, fields), 'scoring_configuration')
  /** Every block of an unsaved draft schema, every diagnostic (the editor's badges, #282). */
  const checkDraft = (schema: Record<string, unknown>) => validate(schema)

  async function runTests(config: ScoringConfig, fields?: Fields) {
    running.value = true
    // publish scores a config without an engine as ClinGen (scoring/registry.py engine_for)
    const scoring = { ...config, engine: config.engine || 'clingen_sop_v11' }
    try {
      results.value = await Promise.all(
        (config.tests ?? []).map(async (test, i) => {
          const name = test.name || `Test ${i + 1}`
          try {
            const r = await validationAPI.validateEvidence({
              evidence_data: test.evidence_data ?? {},
              schema_definition: definition(scoring, fields)
            })
            const got: Record<string, unknown> = {
              total: r.score_calculations.total_score,
              class: r.score_calculations.verdict
            }
            const failures = Object.entries(test.expect ?? {})
              .filter(([key, want]) => got[key] !== want)
              .map(
                ([key, want]) =>
                  `expected ${key} ${JSON.stringify(want)}, got ${JSON.stringify(got[key])}`
              )
            return { name, total: got.total, verdict: got.class, failures }
          } catch (e) {
            return {
              name,
              total: null,
              verdict: null,
              failures: [errorMessage(e, 'scoring failed')]
            }
          }
        })
      )
    } finally {
      running.value = false
    }
  }

  /** Messages for exactly this path. */
  const at = (path: string) => diagnostics.value.filter(d => d.field === path).map(d => d.message)
  /** Number of diagnostics at or under any of these paths (tab badges). */
  const count = (...prefixes: string[]) =>
    diagnostics.value.filter(d =>
      prefixes.some(
        p => d.field === p || d.field.startsWith(`${p}.`) || d.field.startsWith(`${p}[`)
      )
    ).length

  return {
    diagnostics,
    results,
    checking,
    running,
    error,
    check,
    checkDraft,
    runTests,
    at,
    count
  }
}
