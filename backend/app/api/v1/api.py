"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    evidence,
    external_validation,
    gene_assignments,
    gene_summaries,
    genes,
    health,
    logs,
    schema_validation,
    schemas,
    scope_memberships,
    scopes,
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
api_router.include_router(schemas.router, prefix="/schemas", tags=["schemas"])
api_router.include_router(
    schema_validation.router, prefix="/validation", tags=["validation"]
)
api_router.include_router(
    gene_assignments.router, prefix="/gene-assignments", tags=["gene-assignments"]
)
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])

# Core entity endpoints
api_router.include_router(genes.router, prefix="/genes", tags=["genes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# ClinGen SOP v11 endpoints
api_router.include_router(evidence.router, tags=["evidence"])
api_router.include_router(gene_summaries.router, tags=["gene-summaries"])
api_router.include_router(
    external_validation.router, prefix="/external-validation", tags=["external-validation"]
)

# System monitoring endpoints
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
