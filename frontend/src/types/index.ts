// Global type definitions for Gene Curator Frontend

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'curator' | 'viewer'
  isActive: boolean
  createdAt: string
  updatedAt: string
  lastLogin?: string
}

export interface Gene {
  id: string
  symbol: string
  name: string
  alias?: string[]
  chromosome?: string
  start?: number
  end?: number
  strand?: '+' | '-'
  biotype?: string
  description?: string
  omimId?: string
  ensemblId?: string
  ncbiId?: string
  uniprotId?: string
  createdAt: string
  updatedAt: string
  createdBy: string
  updatedBy: string
}

export interface Precuration {
  id: string
  geneId: string
  gene?: Gene
  status: 'draft' | 'in_review' | 'approved' | 'rejected'
  title: string
  description?: string
  rationale?: string
  evidenceSummary?: string
  references?: string[]
  createdAt: string
  updatedAt: string
  createdBy: string
  updatedBy: string
  contributors: string[]
  reviewers?: string[]
  comments?: Array<{
    id: string
    text: string
    author: string
    createdAt: string
  }>
}

export interface Curation {
  id: string
  precurationId: string
  precuration?: Precuration
  verdict: CurationVerdict
  geneticEvidenceScore: number
  experimentalEvidenceScore: number
  totalScore: number
  summaryText?: string
  sopVersion: string
  details: CurationDetails
  status: 'draft' | 'in_review' | 'approved' | 'published'
  createdAt: string
  updatedAt: string
  createdBy: string
  updatedBy: string
  contributors: string[]
  reviewers?: string[]
}

export type CurationVerdict = 
  | 'Definitive'
  | 'Strong' 
  | 'Moderate'
  | 'Limited'
  | 'No Known Disease Relationship'
  | 'Disputed'
  | 'Refuted'

export interface CurationDetails {
  geneticEvidence?: {
    caseLevelData?: EvidenceEntry[]
    segregationData?: EvidenceEntry[]
    caseControlStudies?: EvidenceEntry[]
  }
  experimentalEvidence?: {
    functionalStudies?: EvidenceEntry[]
    modelOrganisms?: EvidenceEntry[]
    rescueExperiments?: EvidenceEntry[]
  }
  contradictoryEvidence?: EvidenceEntry[]
  lumpingSplittingDetails?: {
    rationale: string
    entityDefinition: string
  }
}

export interface EvidenceEntry {
  id: string
  type: string
  description: string
  pmid?: string
  score: number
  notes?: string
  createdAt: string
  createdBy: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface NotificationState {
  show: boolean
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  timeout?: number
}

// API Response types
export interface ApiResponse<T = any> {
  data: T
  message?: string
  status: number
}

export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

// Vue Router types
export interface RouteMetaCustom {
  requiresAuth?: boolean
  roles?: Array<'admin' | 'curator' | 'viewer'>
  title?: string
}

// Form types
export interface FormField {
  key: string
  label: string
  type: 'text' | 'email' | 'password' | 'select' | 'textarea' | 'checkbox' | 'number'
  required?: boolean
  options?: Array<{ value: string; text: string }>
  validation?: (value: any) => boolean | string
}