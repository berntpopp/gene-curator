import { authAPI } from '../auth'
import { scopesAPI } from '../scopes'
import { schemasAPI } from '../schemas'
import { validationAPI } from '../validation'
import { workflowAPI } from '../workflow'
import { genesAPI } from '../genes'
import { assignmentsAPI } from '../assignments'

export type Method = 'get' | 'post' | 'put' | 'patch' | 'delete'

export interface Row {
  name: string
  run: () => Promise<unknown>
  method: Method
  args: unknown[]
  /** Expected resolved value when the mocked response payload is 'payload' */
  result?: unknown
}

export const identityRows: Row[] = [
  // auth
  {
    name: 'auth.login sends only email and password',
    run: () => authAPI.login({ email: 'a@b.c', password: 'pw' } as never),
    method: 'post',
    args: ['/auth/login', { email: 'a@b.c', password: 'pw' }]
  },
  {
    name: 'auth.register',
    run: () => authAPI.register({ email: 'a@b.c' } as never),
    method: 'post',
    args: ['/auth/register', { email: 'a@b.c' }]
  },
  {
    name: 'auth.refresh',
    run: () => authAPI.refresh('r1'),
    method: 'post',
    args: ['/auth/refresh', { refresh_token: 'r1' }]
  },
  { name: 'auth.logout', run: () => authAPI.logout(), method: 'post', args: ['/auth/logout'] },
  { name: 'auth.me', run: () => authAPI.me(), method: 'get', args: ['/auth/me'] },
  {
    name: 'auth.changePassword',
    run: () => authAPI.changePassword({ current_password: 'a' } as never),
    method: 'post',
    args: ['/auth/change-password', { current_password: 'a' }]
  },

  // scopes
  {
    name: 'scopes.getScopes forwards params',
    run: () => scopesAPI.getScopes({ limit: 5 }),
    method: 'get',
    args: ['/scopes', { params: { limit: 5 } }]
  },
  {
    name: 'scopes.getScopeById',
    run: () => scopesAPI.getScopeById('s1'),
    method: 'get',
    args: ['/scopes/s1']
  },
  {
    name: 'scopes.createScope',
    run: () => scopesAPI.createScope({ name: 'n' } as never),
    method: 'post',
    args: ['/scopes', { name: 'n' }]
  },
  {
    name: 'scopes.updateScope',
    run: () => scopesAPI.updateScope('s1', { display_name: 'd' } as never),
    method: 'patch',
    args: ['/scopes/s1', { display_name: 'd' }]
  },
  {
    name: 'scopes.deleteScope without force',
    run: () => scopesAPI.deleteScope('s1'),
    method: 'delete',
    args: ['/scopes/s1', { params: {} }],
    result: undefined
  },
  {
    name: 'scopes.deleteScope with force',
    run: () => scopesAPI.deleteScope('s1', { force: true }),
    method: 'delete',
    args: ['/scopes/s1', { params: { force: true } }],
    result: undefined
  },
  {
    name: 'scopes.getScopeStatistics',
    run: () => scopesAPI.getScopeStatistics('s1'),
    method: 'get',
    args: ['/scopes/s1/statistics']
  },

  // schemas
  {
    name: 'schemas.getSchemas',
    run: () => schemasAPI.getSchemas({ q: 1 }),
    method: 'get',
    args: ['/schemas/curation-schemas', { params: { q: 1 } }]
  },
  {
    name: 'schemas.getSchemaById',
    run: () => schemasAPI.getSchemaById('x'),
    method: 'get',
    args: ['/schemas/curation-schemas/x']
  },
  {
    name: 'schemas.createSchema',
    run: () => schemasAPI.createSchema({ name: 'n' } as never),
    method: 'post',
    args: ['/schemas/curation-schemas', { name: 'n' }]
  },
  {
    name: 'schemas.updateSchema',
    run: () => schemasAPI.updateSchema('x', { name: 'n' } as never),
    method: 'put',
    args: ['/schemas/curation-schemas/x', { name: 'n' }]
  },
  {
    name: 'schemas.validateCurationSchema',
    run: () => schemasAPI.validateCurationSchema('x'),
    method: 'post',
    args: ['/schemas/curation-schemas/x/validate']
  },
  {
    name: 'schemas.deleteSchema',
    run: () => schemasAPI.deleteSchema('x'),
    method: 'delete',
    args: ['/schemas/curation-schemas/x']
  },
  {
    name: 'schemas.getWorkflowPairs',
    run: () => schemasAPI.getWorkflowPairs({ a: 'b' }),
    method: 'get',
    args: ['/schemas/workflow-pairs', { params: { a: 'b' } }]
  },
  {
    name: 'schemas.createWorkflowPair',
    run: () => schemasAPI.createWorkflowPair({ name: 'p' } as never),
    method: 'post',
    args: ['/schemas/workflow-pairs', { name: 'p' }]
  },
  {
    name: 'schemas.getWorkflowPairById',
    run: () => schemasAPI.getWorkflowPairById('p'),
    method: 'get',
    args: ['/schemas/workflow-pairs/p']
  },
  {
    name: 'schemas.updateWorkflowPair',
    run: () => schemasAPI.updateWorkflowPair('p', { name: 'q' } as never),
    method: 'put',
    args: ['/schemas/workflow-pairs/p', { name: 'q' }]
  },
  {
    name: 'schemas.deleteWorkflowPair',
    run: () => schemasAPI.deleteWorkflowPair('p'),
    method: 'delete',
    args: ['/schemas/workflow-pairs/p']
  },

  // validation
  {
    name: 'validation.validateEvidence',
    run: () => validationAPI.validateEvidence({ evidence_data: { a: 1 } }),
    method: 'post',
    args: ['/validation/validate-evidence', { evidence_data: { a: 1 } }]
  },
  {
    name: 'validation.validateSchema',
    run: () => validationAPI.validateSchema({ a: 1 } as never),
    method: 'post',
    args: ['/validation/validate-schema', { a: 1 }]
  },
  {
    name: 'validation.getSupportedFieldTypes',
    run: () => validationAPI.getSupportedFieldTypes(),
    method: 'get',
    args: ['/validation/supported-field-types']
  },
  {
    name: 'validation.getBusinessRules',
    run: () => validationAPI.getBusinessRules(),
    method: 'get',
    args: ['/validation/business-rules']
  },
  {
    name: 'validation.validateField',
    run: () => validationAPI.validateField({ value: 'v' } as never),
    method: 'post',
    args: ['/validation/validate-field', { value: 'v' }]
  },

  // workflow
  {
    name: 'workflow.getWorkflowAnalytics',
    run: () => workflowAPI.getWorkflowAnalytics({ d: 7 }),
    method: 'get',
    args: ['/workflow/analytics', { params: { d: 7 } }]
  },
  {
    name: 'workflow.transitionCuration',
    run: () => workflowAPI.transitionCuration('c1', { target_stage: 'review' }),
    method: 'post',
    args: ['/workflow/curation/c1/transition', { target_stage: 'review' }]
  },
  {
    name: 'workflow.getWorkflowState',
    run: () => workflowAPI.getWorkflowState('precuration', 'p1'),
    method: 'get',
    args: ['/workflow/precuration/p1/state']
  },
  {
    name: 'workflow.getPeerReviewers',
    run: () => workflowAPI.getPeerReviewers({ scope: 's' }),
    method: 'get',
    args: ['/workflow/peer-reviewers', { params: { scope: 's' } }]
  },
  {
    name: 'workflow.submitPeerReview posts to the review submit endpoint',
    run: () => workflowAPI.submitPeerReview('r1', { decision: 'approve' }),
    method: 'post',
    args: ['/workflow/reviews/r1/submit', { decision: 'approve' }]
  },
  {
    name: 'workflow.transitionItem',
    run: () => workflowAPI.transitionItem('precuration', 'p1', { target_stage: 'curation' }),
    method: 'post',
    args: ['/workflow/precuration/p1/transition', { target_stage: 'curation' }]
  },
  {
    name: 'workflow.getWorkflowAuditTrail',
    run: () => workflowAPI.getWorkflowAuditTrail('precuration', 'p1'),
    method: 'get',
    args: ['/workflow/precuration/p1/audit-trail']
  },
  {
    name: 'workflow.getCurationWorkflowHistory',
    run: () => workflowAPI.getCurationWorkflowHistory('c1'),
    method: 'get',
    args: ['/workflow/curation/c1/audit-trail']
  },
  {
    name: 'workflow.getWorkflowStatistics',
    run: () => workflowAPI.getWorkflowStatistics({ s: 1 }),
    method: 'get',
    args: ['/workflow/statistics', { params: { s: 1 } }]
  },

  // genes
  {
    name: 'genes.getGenes',
    run: () => genesAPI.getGenes({ page: 2 }),
    method: 'get',
    args: ['/genes/', { params: { page: 2 } }]
  },
  {
    name: 'genes.getGeneById',
    run: () => genesAPI.getGeneById('g'),
    method: 'get',
    args: ['/genes/g']
  },
  {
    name: 'genes.createGene',
    run: () => genesAPI.createGene({ symbol: 'X' } as never),
    method: 'post',
    args: ['/genes', { symbol: 'X' }]
  },
  {
    name: 'genes.updateGene',
    run: () => genesAPI.updateGene('g', { symbol: 'Y' } as never),
    method: 'put',
    args: ['/genes/g', { symbol: 'Y' }]
  },
  {
    name: 'genes.deleteGene',
    run: () => genesAPI.deleteGene('g'),
    method: 'delete',
    args: ['/genes/g']
  },
  {
    name: 'genes.bulkCreateGenes',
    run: () => genesAPI.bulkCreateGenes({ genes: [] } as never),
    method: 'post',
    args: ['/genes/bulk', { genes: [] }]
  },
  {
    name: 'genes.getGeneAssignments',
    run: () => genesAPI.getGeneAssignments('g'),
    method: 'get',
    args: ['/genes/g/assignments']
  },
  {
    name: 'genes.getGeneCurationProgress',
    run: () => genesAPI.getGeneCurationProgress('g'),
    method: 'get',
    args: ['/genes/g/progress']
  },
  {
    name: 'genes.searchGenes queries GET /genes/search',
    run: () => genesAPI.searchGenes({ query: 'BRCA' }),
    method: 'get',
    args: ['/genes/search', { params: { query: 'BRCA' } }]
  },
  {
    name: 'genes.getStatistics',
    run: () => genesAPI.getStatistics(),
    method: 'get',
    args: ['/genes/statistics']
  },
  {
    name: 'genes.validateGene',
    run: () => genesAPI.validateGene('g'),
    method: 'post',
    args: ['/genes/g/validate']
  },
  {
    name: 'genes.getGeneByHGNC',
    run: () => genesAPI.getGeneByHGNC('HGNC:1100'),
    method: 'get',
    args: ['/genes/hgnc/HGNC:1100']
  },
  {
    name: 'genes.getGeneBySymbol',
    run: () => genesAPI.getGeneBySymbol('BRCA1'),
    method: 'get',
    args: ['/genes/symbol/BRCA1']
  },

  // assignments
  {
    name: 'assignments.getAssignments',
    run: () => assignmentsAPI.getAssignments({ scope: 's' }),
    method: 'get',
    args: ['/gene-assignments', { params: { scope: 's' } }]
  },
  {
    name: 'assignments.getAssignment',
    run: () => assignmentsAPI.getAssignment('a1'),
    method: 'get',
    args: ['/gene-assignments/a1']
  },
  {
    name: 'assignments.createAssignment',
    run: () => assignmentsAPI.createAssignment({ gene_id: 'g' } as never),
    method: 'post',
    args: ['/gene-assignments', { gene_id: 'g' }]
  },
  {
    name: 'assignments.bulkAssignGenes',
    run: () => assignmentsAPI.bulkAssignGenes({ gene_ids: [] } as never),
    method: 'post',
    args: ['/gene-assignments/bulk', { gene_ids: [] }]
  },
  {
    name: 'assignments.getCuratorWorkload',
    run: () => assignmentsAPI.getCuratorWorkload('c'),
    method: 'get',
    args: ['/gene-assignments/curator/c/workload']
  },
  {
    name: 'assignments.getCuratorAssignments',
    run: () => assignmentsAPI.getCuratorAssignments('c', { status: 'open' }),
    method: 'get',
    args: ['/gene-assignments/curator/c/assignments', { params: { status: 'open' } }]
  },
  {
    name: 'assignments.updateAssignmentPriority maps to priority_level',
    run: () => assignmentsAPI.updateAssignmentPriority('a', 'high'),
    method: 'put',
    args: ['/gene-assignments/a', { priority_level: 'high' }]
  },
  {
    name: 'assignments.updateAssignment',
    run: () => assignmentsAPI.updateAssignment('a', { notes: 'n' } as never),
    method: 'put',
    args: ['/gene-assignments/a', { notes: 'n' }]
  },
  {
    name: 'assignments.assignCurator',
    run: () => assignmentsAPI.assignCurator('a', 'c'),
    method: 'post',
    args: ['/gene-assignments/a/assign-curator', { curator_id: 'c' }]
  },
  {
    name: 'assignments.removeAssignment uses the default reason',
    run: () => assignmentsAPI.removeAssignment('a'),
    method: 'delete',
    args: ['/gene-assignments/a', { data: { reason: 'Removed from scope' } }]
  },
  {
    name: 'assignments.removeAssignment with a custom reason',
    run: () => assignmentsAPI.removeAssignment('a', 'Left the project'),
    method: 'delete',
    args: ['/gene-assignments/a', { data: { reason: 'Left the project' } }]
  },
  {
    name: 'assignments.getAssignmentsByScope',
    run: () => assignmentsAPI.getAssignmentsByScope('s', { q: 1 }),
    method: 'get',
    args: ['/gene-assignments/scope/s', { params: { q: 1 } }]
  },
  {
    name: 'assignments.getAvailableGenesForScope',
    run: () => assignmentsAPI.getAvailableGenesForScope('s'),
    method: 'get',
    args: ['/gene-assignments/scope/s/available-genes']
  },
  {
    name: 'assignments.getScopeAssignmentOverview',
    run: () => assignmentsAPI.getScopeAssignmentOverview('s'),
    method: 'get',
    args: ['/gene-assignments/scope/s/overview']
  }
]
