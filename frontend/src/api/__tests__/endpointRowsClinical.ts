import { curationsAPI } from '../curations'
import { precurationsAPI } from '../precurations'
import { externalValidationAPI } from '../externalValidation'
import { geneSummaryAPI } from '../geneSummary'
import { invitationsApi } from '../invitations'
import { notificationsAPI } from '../notifications'
import { ontologyAPI } from '../ontology'
import { publicationsAPI } from '../publications'
import type { Row } from './endpointRows'

export const clinicalRows: Row[] = [
  // curations
  {
    name: 'curations.getCurations',
    run: () => curationsAPI.getCurations({ status: 'draft' }),
    method: 'get',
    args: ['/curations/', { params: { status: 'draft' } }]
  },
  {
    name: 'curations.getCuration',
    run: () => curationsAPI.getCuration('c'),
    method: 'get',
    args: ['/curations/c', { params: { detail: true } }]
  },
  {
    name: 'curations.createCuration',
    run: () => curationsAPI.createCuration({ gene_id: 'g' } as never),
    method: 'post',
    args: ['/curations/', { gene_id: 'g' }]
  },
  {
    name: 'curations.updateCuration',
    run: () => curationsAPI.updateCuration('c', { lock_version: 2 } as never),
    method: 'put',
    args: ['/curations/c', { lock_version: 2 }, { params: { detail: true } }]
  },
  {
    name: 'curations.saveDraft',
    run: () => curationsAPI.saveDraft('c', { draft: true } as never),
    method: 'patch',
    args: ['/curations/c/draft', { draft: true }, { params: { detail: true } }]
  },
  {
    name: 'curations.submitCuration defaults to an empty body',
    run: () => curationsAPI.submitCuration('c'),
    method: 'post',
    args: ['/curations/c/submit', {}, { params: { detail: true } }]
  },
  {
    name: 'curations.deleteCuration',
    run: () => curationsAPI.deleteCuration('c'),
    method: 'delete',
    args: ['/curations/c'],
    result: undefined
  },
  {
    name: 'curations.calculateScore',
    run: () => curationsAPI.calculateScore('c'),
    method: 'get',
    args: ['/curations/c/score']
  },

  // precurations
  {
    name: 'precurations.getPrecurations',
    run: () => precurationsAPI.getPrecurations({ q: 1 }),
    method: 'get',
    args: ['/precurations/', { params: { q: 1 } }]
  },
  {
    name: 'precurations.getPrecuration',
    run: () => precurationsAPI.getPrecuration('p'),
    method: 'get',
    args: ['/precurations/p']
  },
  {
    name: 'precurations.createPrecuration',
    run: () => precurationsAPI.createPrecuration({ gene_id: 'g' } as never),
    method: 'post',
    args: ['/precurations/', { gene_id: 'g' }]
  },
  {
    name: 'precurations.updatePrecuration',
    run: () => precurationsAPI.updatePrecuration('p', { lock_version: 1 } as never),
    method: 'put',
    args: ['/precurations/p', { lock_version: 1 }]
  },
  {
    name: 'precurations.saveDraft',
    run: () => precurationsAPI.saveDraft('p', { evidence_data: {}, lock_version: 0 }),
    method: 'patch',
    args: ['/precurations/p/draft', { evidence_data: {}, lock_version: 0 }]
  },
  {
    name: 'precurations.submitPrecuration sends the loaded version',
    run: () => precurationsAPI.submitPrecuration('p', { notes: null, lock_version: 2 }),
    method: 'post',
    args: ['/precurations/p/submit', { notes: null, lock_version: 2 }]
  },
  {
    name: 'precurations.completePrecuration',
    run: () => precurationsAPI.completePrecuration('p'),
    method: 'post',
    args: ['/precurations/p/complete']
  },
  {
    name: 'precurations.approvePrecuration',
    run: () => precurationsAPI.approvePrecuration('p'),
    method: 'post',
    args: ['/precurations/p/approve']
  },
  {
    name: 'precurations.rejectPrecuration',
    run: () => precurationsAPI.rejectPrecuration('p', { reason: 'r' }),
    method: 'post',
    args: ['/precurations/p/reject', { reason: 'r' }]
  },
  {
    name: 'precurations.deletePrecuration',
    run: () => precurationsAPI.deletePrecuration('p'),
    method: 'delete',
    args: ['/precurations/p'],
    result: undefined
  },
  {
    name: 'precurations.getPrecurationsByGeneAndScope',
    run: () => precurationsAPI.getPrecurationsByGeneAndScope('g', 's'),
    method: 'get',
    args: ['/precurations/', { params: { gene_id: 'g', scope_id: 's' } }]
  },

  // external validation
  {
    name: 'externalValidation.validateHGNC',
    run: () => externalValidationAPI.validateHGNC('BRCA1'),
    method: 'post',
    args: [
      '/external-validation/validate/hgnc',
      null,
      { params: { gene_symbol: 'BRCA1', skip_cache: false } }
    ]
  },
  {
    name: 'externalValidation.validatePubMed honours skipCache',
    run: () => externalValidationAPI.validatePubMed('123', true),
    method: 'post',
    args: [
      '/external-validation/validate/pubmed',
      null,
      { params: { pmid: '123', skip_cache: true } }
    ]
  },
  {
    name: 'externalValidation.validateHPO',
    run: () => externalValidationAPI.validateHPO('HP:0001250'),
    method: 'post',
    args: [
      '/external-validation/validate/hpo',
      null,
      { params: { hpo_term: 'HP:0001250', skip_cache: false } }
    ]
  },
  {
    name: 'externalValidation.validateBatch',
    run: () => externalValidationAPI.validateBatch('hgnc', ['A', 'B']),
    method: 'post',
    args: ['/external-validation/validate/batch', { validator_name: 'hgnc', values: ['A', 'B'] }]
  },
  {
    name: 'externalValidation.getCacheStatistics',
    run: () => externalValidationAPI.getCacheStatistics(),
    method: 'get',
    args: ['/external-validation/cache/statistics']
  },
  {
    name: 'externalValidation.searchHGNC defaults the limit',
    run: () => externalValidationAPI.searchHGNC('brca'),
    method: 'post',
    args: ['/external-validation/hgnc/search', { query: 'brca', limit: 10 }]
  },
  {
    name: 'externalValidation.fetchHGNCGene',
    run: () => externalValidationAPI.fetchHGNCGene('HGNC:1100'),
    method: 'get',
    args: ['/external-validation/hgnc/fetch/HGNC:1100']
  },

  // gene summary
  {
    name: 'geneSummary.getFullSummary',
    run: () => geneSummaryAPI.getFullSummary('g'),
    method: 'get',
    args: ['/genes/g/summary/full']
  },

  // invitations
  {
    name: 'invitations.getPendingInvitations without expired entries',
    run: () => invitationsApi.getPendingInvitations(),
    method: 'get',
    args: ['/me/invitations', { params: {} }]
  },
  {
    name: 'invitations.getPendingInvitations including expired entries',
    run: () => invitationsApi.getPendingInvitations({ includeExpired: true }),
    method: 'get',
    args: ['/me/invitations', { params: { include_expired: true } }]
  },
  {
    name: 'invitations.acceptInvitation',
    run: () => invitationsApi.acceptInvitation('s1', 'i1'),
    method: 'post',
    args: ['/scopes/s1/invitations/i1/accept']
  },
  {
    name: 'invitations.declineInvitation',
    run: () => invitationsApi.declineInvitation('i1'),
    method: 'post',
    args: ['/invitations/i1/decline'],
    result: undefined
  },

  // notifications
  {
    name: 'notifications.getNotifications',
    run: () => notificationsAPI.getNotifications({ is_read: false }),
    method: 'get',
    args: ['/notifications/', { params: { is_read: false } }]
  },
  {
    name: 'notifications.markAsRead',
    run: () => notificationsAPI.markAsRead('n1'),
    method: 'patch',
    args: ['/notifications/n1/read']
  },
  {
    name: 'notifications.markAllAsRead',
    run: () => notificationsAPI.markAllAsRead(),
    method: 'patch',
    args: ['/notifications/read-all']
  },

  // ontology
  {
    name: 'ontology.searchMONDO',
    run: () => ontologyAPI.searchMONDO('ataxia'),
    method: 'post',
    args: ['/ontology/mondo/search', { query: 'ataxia', limit: 10 }]
  },
  {
    name: 'ontology.searchOMIM',
    run: () => ontologyAPI.searchOMIM('ogden', 5),
    method: 'post',
    args: ['/ontology/omim/search', { query: 'ogden', limit: 5 }]
  },
  {
    name: 'ontology.getOMIMDisease encodes the id',
    run: () => ontologyAPI.getOMIMDisease('OMIM:300855'),
    method: 'get',
    args: ['/ontology/omim/OMIM%3A300855']
  },
  {
    name: 'ontology.searchHPO',
    run: () => ontologyAPI.searchHPO('seizure'),
    method: 'post',
    args: ['/ontology/hpo/search', { query: 'seizure', limit: 10 }]
  },
  {
    name: 'ontology.validateHPO encodes the id',
    run: () => ontologyAPI.validateHPO('HP:0001250'),
    method: 'get',
    args: ['/ontology/hpo/HP%3A0001250/validate']
  },
  {
    name: 'ontology.getInheritancePatterns',
    run: () => ontologyAPI.getInheritancePatterns(),
    method: 'get',
    args: ['/ontology/hpo/inheritance']
  },

  // publications
  {
    name: 'publications.validatePMIDs',
    run: () => publicationsAPI.validatePMIDs(['1', '2']),
    method: 'post',
    args: ['/publications/validate', { pmids: ['1', '2'] }]
  },
  {
    name: 'publications.getPublication',
    run: () => publicationsAPI.getPublication('123'),
    method: 'get',
    args: ['/publications/123']
  },
  {
    name: 'publications.listPublications with defaults',
    run: () => publicationsAPI.listPublications(),
    method: 'get',
    args: ['/publications', { params: { skip: 0, limit: 50 } }]
  },
  {
    name: 'publications.listPublications with a search term',
    run: () => publicationsAPI.listPublications({ skip: 10, limit: 5, search: 'kidney' }),
    method: 'get',
    args: ['/publications', { params: { skip: 10, limit: 5, search: 'kidney' } }]
  },
  {
    name: 'publications.getStats',
    run: () => publicationsAPI.getStats(),
    method: 'get',
    args: ['/publications/stats/count']
  }
]
