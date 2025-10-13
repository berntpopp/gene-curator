/**
 * Terminology Glossary
 *
 * Centralized terminology definitions to ensure consistency across the application.
 * Use these constants throughout the codebase to avoid terminology conflicts.
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#appendix-c-terminology-glossary
 */

export const TERMINOLOGY = {
  // Core Concepts
  ASSIGNMENT: 'Assignment',
  GENE_ASSIGNMENT: 'Gene Assignment', // Deprecated - use ASSIGNMENT
  SCOPE_ASSIGNMENT: 'Scope Assignment', // Deprecated - use ASSIGNMENT

  // Curation Configuration
  CURATION_SETUP: 'Curation Setup',
  METHODOLOGY_CONFIG: 'Methodology Configuration', // Deprecated
  SCHEMA_MANAGEMENT: 'Schema Management', // Deprecated

  // Evidence Collection
  TEMPLATES: 'Templates',
  SCHEMAS: 'Schemas', // Deprecated - use TEMPLATES
  METHODOLOGIES: 'Methodologies', // Deprecated - use TEMPLATES

  // Workflow
  WORKFLOWS: 'Workflows',
  WORKFLOW_PAIRS: 'Workflow Pairs', // Deprecated - use WORKFLOWS
  METHODOLOGY_PAIRS: 'Methodology Pairs', // Deprecated - use WORKFLOWS

  // Gene Browser
  GENE_CATALOG: 'Gene Catalog',
  BROWSE: 'Browse', // Deprecated - too vague
  GENES: 'Genes', // Deprecated - use GENE_CATALOG

  // Quality Control
  VALIDATION: 'Validation',
  QUALITY_CONTROL: 'Quality Control', // Deprecated - use VALIDATION
  QC: 'QC', // Deprecated - use VALIDATION

  // Organization
  CLINICAL_SCOPE: 'Clinical Scope',
  SCOPE: 'Scope', // Short form acceptable in context
  SPECIALTY: 'Specialty', // Deprecated - use CLINICAL_SCOPE
  DOMAIN: 'Domain', // Deprecated - use CLINICAL_SCOPE

  // Work Views
  MY_WORK: 'My Work',
  MY_ASSIGNMENTS: 'My Assignments', // Deprecated - use MY_WORK
  TEAM_WORK: 'Team Work',
  BROWSE_ASSIGNMENTS: 'Browse Assignments', // Deprecated - use TEAM_WORK

  // User Roles
  VIEWER: 'Viewer',
  CURATOR: 'Curator',
  REVIEWER: 'Reviewer',
  ADMIN: 'Admin',
  SCOPE_ADMIN: 'Scope Admin',

  // Workflow Stages
  ENTRY: 'Entry',
  PRECURATION: 'Precuration',
  CURATION: 'Curation',
  REVIEW: 'Review',
  ACTIVE: 'Active',
  ARCHIVED: 'Archived',

  // Status
  DRAFT: 'Draft',
  SUBMITTED: 'Submitted',
  IN_REVIEW: 'In Review',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  PENDING: 'Pending',
  COMPLETED: 'Completed'
}

/**
 * Get user-friendly label for a term
 * @param {string} key - The terminology key
 * @returns {string} The user-friendly label
 */
export function getTermLabel(key) {
  return TERMINOLOGY[key] || key
}

/**
 * Check if a term is deprecated
 * @param {string} term - The term to check
 * @returns {boolean} True if deprecated
 */
export function isDeprecated(term) {
  const deprecatedTerms = [
    'GENE_ASSIGNMENT',
    'SCOPE_ASSIGNMENT',
    'METHODOLOGY_CONFIG',
    'SCHEMA_MANAGEMENT',
    'SCHEMAS',
    'METHODOLOGIES',
    'WORKFLOW_PAIRS',
    'METHODOLOGY_PAIRS',
    'BROWSE',
    'GENES',
    'QUALITY_CONTROL',
    'QC',
    'SPECIALTY',
    'DOMAIN',
    'MY_ASSIGNMENTS',
    'BROWSE_ASSIGNMENTS'
  ]
  return deprecatedTerms.includes(term)
}

export default TERMINOLOGY
