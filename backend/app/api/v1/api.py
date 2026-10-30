"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    curations,
    external_validation,
    gene_assignments,
    gene_catalogue,
    gene_catalogue_matrix,
    gene_resolve,
    gene_search,
    gene_summaries,
    genes,
    health,
    invitations,
    llm_admin,
    llm_prompts,
    llm_runs,
    llm_scope,
    logs,
    my_work,
    notifications,
    ontology,
    personal_access_tokens,
    precurations,
    publications,
    review_comments,
    schema_validation,
    schemas,
    scope_memberships,
    scopes,
    search,
    users,
    workflow,
)

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Methodology-agnostic system endpoints
api_router.include_router(scopes.router, prefix="/scopes", tags=["scopes"])
api_router.include_router(
    scope_memberships.router, prefix="/scopes", tags=["scope-memberships"]
)
api_router.include_router(
    invitations.router, tags=["invitations"]
)  # User-facing invitation endpoints (/me/invitations, /invitations/{id}/...)
api_router.include_router(llm_scope.router, prefix="/scopes", tags=["llm"])
api_router.include_router(my_work.router, tags=["my-work"])  # /me/work
api_router.include_router(
    personal_access_tokens.router, prefix="/me/tokens", tags=["tokens"]
)
api_router.include_router(schemas.router, prefix="/schemas", tags=["schemas"])
api_router.include_router(
    schema_validation.router, prefix="/validation", tags=["validation"]
)
api_router.include_router(
    gene_assignments.router, prefix="/gene-assignments", tags=["gene-assignments"]
)
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(curations.router, prefix="/curations", tags=["curations"])
api_router.include_router(
    review_comments.router, prefix="/curations", tags=["review-comments"]
)
api_router.include_router(
    precurations.router, prefix="/precurations", tags=["precurations"]
)

# Core entity endpoints
api_router.include_router(gene_resolve.router, prefix="/genes", tags=["genes"])
api_router.include_router(gene_search.router, prefix="/genes", tags=["genes"])
api_router.include_router(genes.router, prefix="/genes", tags=["genes"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Gene Catalogue - read-only aggregation view
api_router.include_router(
    gene_catalogue.router, prefix="/gene-catalogue", tags=["gene-catalogue"]
)

# ClinGen SOP v11 endpoints
api_router.include_router(
    gene_catalogue_matrix.router,
    prefix="/gene-catalogue",
    tags=["gene-catalogue"],
)
api_router.include_router(gene_summaries.router, tags=["gene-summaries"])
api_router.include_router(
    external_validation.router,
    prefix="/external-validation",
    tags=["external-validation"],
)
api_router.include_router(
    ontology.router,
    prefix="/ontology",
    tags=["ontology"],
)
api_router.include_router(
    publications.router,
    prefix="/publications",
    tags=["publications"],
)

# Notification endpoints
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)

# LLM admin console (platform admins)
api_router.include_router(llm_admin.router, prefix="/admin/llm", tags=["llm-admin"])
api_router.include_router(llm_prompts.router, prefix="/admin/llm", tags=["llm-admin"])
api_router.include_router(llm_runs.router, tags=["llm"])  # full paths, no prefix

# System monitoring endpoints
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
