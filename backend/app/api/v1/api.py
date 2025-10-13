"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    gene_assignments,
    genes_new,
    health,
    logs,
    schema_validation,
    schemas,
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
api_router.include_router(schemas.router, prefix="/schemas", tags=["schemas"])
api_router.include_router(
    schema_validation.router, prefix="/validation", tags=["validation"]
)
api_router.include_router(
    gene_assignments.router, prefix="/gene-assignments", tags=["gene-assignments"]
)
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])

# Core entity endpoints
api_router.include_router(genes_new.router, prefix="/genes", tags=["genes"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# System monitoring endpoints
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
