"""
System status and health monitoring endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.models.schemas import SystemStatusResponse
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(db: Session = Depends(get_database)):
    """
    Get overall system status and health information.
    
    Args:
        db: Database session
        
    Returns:
        SystemStatusResponse: System status information
    """
    indexing_service = IndexingService(db)
    status_info = indexing_service.get_system_status()
    
    if "error" in status_info:
        # If there's an error, return a basic status structure
        return SystemStatusResponse(
            documents_by_status={},
            vector_store={"status": "error", "error": status_info["error"]},
            embedding_service={"status": "error"},
            services_connected={
                "database": True,  # If we got here, DB is connected
                "vector_store": False,
                "embedding_api": False
            }
        )
    
    return SystemStatusResponse(**status_info)


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for the system.
    
    Returns:
        dict: Basic health status
    """
    return {
        "status": "healthy",
        "service": "DocuRAG System",
        "message": "System is operational"
    } 