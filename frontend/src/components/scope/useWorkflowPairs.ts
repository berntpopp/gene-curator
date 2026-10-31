import { ref } from 'vue'
import { schemasAPI } from '@/api/schemas'
import { logService } from '@/services/logService'

/** Workflow pair with the names of its linked schemas (the API returns only their ids) */
export interface WorkflowPairOption {
  id: string
  name: string
  version: string
  description?: string | null
  precuration_schema_name?: string
  curation_schema_name?: string
  displayName: string
  owner_scope_id?: string | null
}

interface PairScope {
  default_workflow_pair_id?: string | null
  allowed_workflow_pair_ids?: string[] | null
}

/** Ids of the scope's default and allowed pairs (#284); null when neither is configured. */
export function allowedPairIds(scope?: PairScope | null): Set<string> | null {
  const ids = [scope?.default_workflow_pair_id, ...(scope?.allowed_workflow_pair_ids ?? [])]
  const set = new Set(ids.filter((id): id is string => !!id))
  return set.size ? set : null
}

/** The pairs the scope may use; a scope with nothing configured allows all. */
export function allowedPairs<T extends { id: string }>(pairs: T[], scope?: PairScope | null): T[] {
  const ids = allowedPairIds(scope)
  return ids ? pairs.filter(pair => ids.has(pair.id)) : pairs
}

/** Loads the active workflow pairs (methodologies) for a select; shared by scope create and settings. */
export function useWorkflowPairs(onError: (message: string) => void) {
  const workflowPairs = ref<WorkflowPairOption[]>([])
  const loading = ref(false)

  async function loadWorkflowPairs() {
    loading.value = true
    try {
      const [pairs, schemas] = await Promise.all([
        schemasAPI.getWorkflowPairs({ active_only: true }),
        schemasAPI.getSchemas()
      ])
      const schemaNames = new Map(schemas.map(schema => [schema.id, schema.name]))
      workflowPairs.value = pairs.map(pair => ({
        id: pair.id,
        name: pair.name,
        version: pair.version,
        description: pair.description,
        precuration_schema_name: schemaNames.get(pair.precuration_schema_id),
        curation_schema_name: schemaNames.get(pair.curation_schema_id),
        displayName: `${pair.name} (${pair.version})`,
        owner_scope_id: pair.owner_scope_id
      }))
    } catch (error) {
      logService.error('Failed to load workflow pairs', {
        error: error instanceof Error ? error.message : undefined
      })
      onError('Failed to load workflow pairs')
    } finally {
      loading.value = false
    }
  }

  return { workflowPairs, loading, loadWorkflowPairs }
}
