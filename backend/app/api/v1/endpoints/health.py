"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_database, get_settings
from app.config.settings import Settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Basic health status
    """
    return {
        "status": "healthy",
        "service": "DocuRAG Backend",
        "message": "Service is running"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_database),
    settings: Settings = Depends(get_settings)
):
    """
    Detailed health check that verifies database connectivity and configuration.
    
    Args:
        db: Database session
        settings: Application settings
        
    Returns:
        dict: Detailed health status
        
    Raises:
        HTTPException: If any health check fails
    """
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {}
    }
    
    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check configuration
    try:
        # Verify critical settings are configured
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        health_status["checks"]["configuration"] = {
            "status": "healthy",
            "message": "Configuration valid"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["configuration"] = {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }
    
    # If any check failed, return 503
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready")
async def readiness_check(
    db: Session = Depends(get_database),
):
    """
    Readiness check for Kubernetes/Docker deployments.
    
    Args:
        db: Database session
        
    Returns:
        dict: Readiness status
        
    Raises:
        HTTPException: If service is not ready
    """
    try:
        # Check if database is accessible
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "message": "Service is ready to accept requests"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not ready",
                "message": f"Service is not ready: {str(e)}"
            }
        ) 