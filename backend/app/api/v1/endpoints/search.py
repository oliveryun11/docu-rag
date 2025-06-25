"""
RAG search API endpoints for querying documents and generating answers.
"""

import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.models.schemas import (
    RAGSearchRequest, RAGSearchResponse,
    SimilaritySearchRequest, SimilaritySearchResponse
)
from app.services.search_service import RAGSearchService

router = APIRouter()


@router.post("/", response_model=RAGSearchResponse)
async def rag_search(
    request: RAGSearchRequest,
    db: Session = Depends(get_database)
):
    """
    Perform RAG search - retrieve relevant chunks and generate an answer.
    
    Args:
        request: RAG search request with query and filters
        db: Database session
        
    Returns:
        RAGSearchResponse: Generated answer with sources
        
    Raises:
        HTTPException: If search fails
    """
    start_time = time.time()
    
    try:
        search_service = RAGSearchService(db)
        
        # Perform RAG search
        result = search_service.search(
            query=request.query,
            k=request.k,
            document_ids=request.document_ids,
            file_types=request.file_types,
            min_similarity=request.min_similarity
        )
        
        # Generate related questions if requested
        related_questions = None
        if request.include_related_questions and result["search_results"]:
            context = search_service._prepare_context(
                [{"document": chunk["content"], "metadata": chunk["metadata"]} 
                 for chunk in result["search_results"]]
            )
            related_questions = search_service.get_related_questions(request.query, context)
        
        response_time = time.time() - start_time
        
        return RAGSearchResponse(
            answer=result["answer"],
            sources=result["sources"],
            query=result["query"],
            total_chunks=result["total_chunks"],
            search_results=result["search_results"],
            related_questions=related_questions,
            response_time_seconds=round(response_time, 3)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e)}")


@router.post("/similarity", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    db: Session = Depends(get_database)
):
    """
    Perform similarity search without LLM generation (for exploration/browsing).
    
    Args:
        request: Similarity search request
        db: Database session
        
    Returns:
        SimilaritySearchResponse: Search results without generated answer
        
    Raises:
        HTTPException: If search fails
    """
    start_time = time.time()
    
    try:
        search_service = RAGSearchService(db)
        
        # Perform similarity search only
        result = search_service.similarity_search_only(
            query=request.query,
            k=request.k,
            document_ids=request.document_ids,
            file_types=request.file_types,
            min_similarity=request.min_similarity
        )
        
        response_time = time.time() - start_time
        
        return SimilaritySearchResponse(
            sources=result["sources"],
            query=result["query"],
            total_chunks=result["total_chunks"],
            search_results=result["search_results"],
            response_time_seconds=round(response_time, 3)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


@router.get("/", response_model=RAGSearchResponse)
async def rag_search_get(
    q: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    k: int = Query(default=5, ge=1, le=20, description="Number of chunks to retrieve"),
    min_similarity: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    document_ids: Optional[str] = Query(default=None, description="Comma-separated document IDs"),
    file_types: Optional[str] = Query(default=None, description="Comma-separated file types"),
    include_related: bool = Query(default=True, description="Include related questions"),
    db: Session = Depends(get_database)
):
    """
    Perform RAG search via GET request (convenient for testing and simple integrations).
    
    Args:
        q: Search query
        k: Number of chunks to retrieve
        min_similarity: Minimum similarity threshold
        document_ids: Comma-separated document IDs (optional)
        file_types: Comma-separated file types (optional)
        include_related: Include related questions
        db: Database session
        
    Returns:
        RAGSearchResponse: Generated answer with sources
    """
    # Parse comma-separated values
    parsed_document_ids = None
    if document_ids:
        try:
            parsed_document_ids = [int(doc_id.strip()) for doc_id in document_ids.split(",") if doc_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_ids format. Use comma-separated integers.")
    
    parsed_file_types = None
    if file_types:
        parsed_file_types = [ft.strip() for ft in file_types.split(",") if ft.strip()]
    
    # Create request object
    request = RAGSearchRequest(
        query=q,
        k=k,
        min_similarity=min_similarity,
        document_ids=parsed_document_ids,
        file_types=parsed_file_types,
        include_related_questions=include_related
    )
    
    # Use the POST endpoint logic
    return await rag_search(request, db)


@router.get("/similarity", response_model=SimilaritySearchResponse)
async def similarity_search_get(
    q: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    k: int = Query(default=10, ge=1, le=50, description="Number of chunks to retrieve"),
    min_similarity: float = Query(default=0.0, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    document_ids: Optional[str] = Query(default=None, description="Comma-separated document IDs"),
    file_types: Optional[str] = Query(default=None, description="Comma-separated file types"),
    db: Session = Depends(get_database)
):
    """
    Perform similarity search via GET request.
    
    Args:
        q: Search query
        k: Number of chunks to retrieve
        min_similarity: Minimum similarity threshold
        document_ids: Comma-separated document IDs (optional)
        file_types: Comma-separated file types (optional)
        db: Database session
        
    Returns:
        SimilaritySearchResponse: Search results without generated answer
    """
    # Parse comma-separated values
    parsed_document_ids = None
    if document_ids:
        try:
            parsed_document_ids = [int(doc_id.strip()) for doc_id in document_ids.split(",") if doc_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_ids format. Use comma-separated integers.")
    
    parsed_file_types = None
    if file_types:
        parsed_file_types = [ft.strip() for ft in file_types.split(",") if ft.strip()]
    
    # Create request object
    request = SimilaritySearchRequest(
        query=q,
        k=k,
        min_similarity=min_similarity,
        document_ids=parsed_document_ids,
        file_types=parsed_file_types
    )
    
    # Use the POST endpoint logic
    return await similarity_search(request, db)


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Partial query"),
    limit: int = Query(default=5, ge=1, le=10, description="Maximum suggestions"),
    db: Session = Depends(get_database)
):
    """
    Get search suggestions based on partial query (future enhancement).
    
    Args:
        q: Partial search query
        limit: Maximum number of suggestions
        db: Database session
        
    Returns:
        Dict: Search suggestions
    """
    try:
        search_service = RAGSearchService(db)
        suggestions = search_service.get_search_suggestions(q, limit)
        
        return {
            "query": q,
            "suggestions": suggestions,
            "total": len(suggestions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get search suggestions: {str(e)}")


@router.post("/related-questions")
async def get_related_questions(
    query: str,
    context: str,
    db: Session = Depends(get_database)
):
    """
    Generate related questions based on a query and context.
    
    Args:
        query: Original query
        context: Context text
        db: Database session
        
    Returns:
        Dict: Related questions
    """
    try:
        search_service = RAGSearchService(db)
        questions = search_service.get_related_questions(query, context)
        
        return {
            "original_query": query,
            "related_questions": questions,
            "total": len(questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate related questions: {str(e)}") 