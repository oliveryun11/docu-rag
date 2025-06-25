"""
Document management API endpoints.
"""

import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.models.schemas import (
    DocumentResponse, DocumentListResponse, DocumentUpdate, 
    DocumentStats, ChunkResponse, ChunkListResponse, FileUploadResponse,
    ProcessingStatusResponse, ProcessingTriggerResponse, SystemStatusResponse
)
from app.models.enums import DocumentStatus, FileType
from app.services.document_processor import DocumentService
from app.services.indexing_service import IndexingService
from app.utils.file_handlers import format_file_size

router = APIRouter()


@router.post("/", response_model=FileUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    """
    Upload a new document.
    
    Args:
        file: Uploaded file
        db: Database session
        
    Returns:
        FileUploadResponse: Upload result with document details
    """
    import time
    start_time = time.time()
    
    service = DocumentService(db)
    document = await service.create_document(file)
    
    upload_time = time.time() - start_time
    
    return FileUploadResponse(
        message=f"Document '{file.filename}' uploaded successfully",
        document=DocumentResponse.model_validate(document),
        upload_time_seconds=round(upload_time, 3)
    )


@router.post("/{document_id}/process", response_model=ProcessingTriggerResponse)
async def process_document(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Start processing a document (extract text, generate embeddings, index).
    
    Args:
        document_id: Document ID to process
        db: Database session
        
    Returns:
        ProcessingTriggerResponse: Processing trigger confirmation
        
    Raises:
        HTTPException: If document not found or processing fails to start
    """
    service = DocumentService(db)
    indexing_service = IndexingService(db)
    
    # Check if document exists
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if document is in a processable state
    if document.status not in [DocumentStatus.UPLOADED.value, DocumentStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Document is already {document.status}. Only uploaded or failed documents can be processed."
        )
    
    try:
        # Start processing (this runs synchronously for now)
        success = indexing_service.process_document(document_id)
        
        if success:
            return ProcessingTriggerResponse(
                message=f"Document '{document.original_filename}' processed successfully",
                document_id=document_id,
                status="indexed",
                triggered_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Document processing failed. Check processing status for details."
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start document processing: {str(e)}"
        )


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Get detailed processing status for a document.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        ProcessingStatusResponse: Detailed processing status
        
    Raises:
        HTTPException: If document not found
    """
    indexing_service = IndexingService(db)
    
    status_info = indexing_service.get_processing_status(document_id)
    
    if "error" in status_info:
        raise HTTPException(status_code=404, detail=status_info["error"])
    
    return ProcessingStatusResponse(**status_info)


@router.post("/{document_id}/reprocess", response_model=ProcessingTriggerResponse)
async def reprocess_document(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Reprocess a document (useful for failed documents or updates).
    
    Args:
        document_id: Document ID to reprocess
        db: Database session
        
    Returns:
        ProcessingTriggerResponse: Reprocessing trigger confirmation
        
    Raises:
        HTTPException: If document not found or reprocessing fails
    """
    service = DocumentService(db)
    indexing_service = IndexingService(db)
    
    # Check if document exists
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Start reprocessing
        success = indexing_service.reprocess_document(document_id)
        
        if success:
            return ProcessingTriggerResponse(
                message=f"Document '{document.original_filename}' reprocessed successfully",
                document_id=document_id,
                status="indexed",
                triggered_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Document reprocessing failed. Check processing status for details."
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reprocess document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[DocumentStatus] = Query(default=None, description="Filter by status"),
    file_type: Optional[FileType] = Query(default=None, description="Filter by file type"),
    search: Optional[str] = Query(default=None, description="Search in filename or title"),
    db: Session = Depends(get_database)
):
    """
    Get paginated list of documents.
    
    Args:
        page: Page number (1-based)
        page_size: Items per page
        status: Filter by document status
        file_type: Filter by file type
        search: Search term
        db: Database session
        
    Returns:
        DocumentListResponse: Paginated document list
    """
    service = DocumentService(db)
    
    skip = (page - 1) * page_size
    documents, total = service.get_documents(
        skip=skip,
        limit=page_size,
        status=status,
        file_type=file_type,
        search=search
    )
    
    # Add chunk count to each document
    document_responses = []
    for doc in documents:
        doc_response = DocumentResponse.model_validate(doc)
        doc_response.chunk_count = len(doc.chunks)
        document_responses.append(doc_response)
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    return DocumentListResponse(
        documents=document_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=DocumentStats)
async def get_document_stats(db: Session = Depends(get_database)):
    """
    Get document statistics.
    
    Args:
        db: Database session
        
    Returns:
        DocumentStats: Document statistics
    """
    service = DocumentService(db)
    return service.get_document_stats()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Get document by ID.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        DocumentResponse: Document details
        
    Raises:
        HTTPException: If document not found
    """
    service = DocumentService(db)
    document = service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_response = DocumentResponse.model_validate(document)
    doc_response.chunk_count = len(document.chunks)
    
    return doc_response


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    db: Session = Depends(get_database)
):
    """
    Update document metadata.
    
    Args:
        document_id: Document ID
        update_data: Update data
        db: Database session
        
    Returns:
        DocumentResponse: Updated document
        
    Raises:
        HTTPException: If document not found
    """
    service = DocumentService(db)
    document = service.update_document(document_id, update_data)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_response = DocumentResponse.model_validate(document)
    doc_response.chunk_count = len(document.chunks)
    
    return doc_response


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Delete document and associated files.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        dict: Deletion confirmation
        
    Raises:
        HTTPException: If document not found
    """
    service = DocumentService(db)
    
    # Get document details before deletion
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete document
    success = service.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    
    return {
        "message": f"Document '{document.original_filename}' deleted successfully",
        "document_id": document_id
    }


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(
    document_id: int,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_database)
):
    """
    Get document chunks with pagination.
    
    Args:
        document_id: Document ID
        page: Page number (1-based)
        page_size: Items per page
        db: Database session
        
    Returns:
        ChunkListResponse: Paginated chunk list
        
    Raises:
        HTTPException: If document not found
    """
    service = DocumentService(db)
    
    # Verify document exists
    document = service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get all chunks for this document
    all_chunks = service.get_document_chunks(document_id)
    total = len(all_chunks)
    
    # Apply pagination
    skip = (page - 1) * page_size
    chunks = all_chunks[skip:skip + page_size]
    
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    chunk_responses = [ChunkResponse.model_validate(chunk) for chunk in chunks]
    
    return ChunkListResponse(
        chunks=chunk_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    ) 