"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, documents, system, search, embeddings

# Create API v1 router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    health.router,
    tags=["health"]
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["search", "rag"]
)

api_router.include_router(
    embeddings.router,
    prefix="/embeddings",
    tags=["embeddings", "debug"]
)

api_router.include_router(
    system.router,
    prefix="/system",
    tags=["system"]
) 