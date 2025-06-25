"""
Embedding visualization and testing API endpoints.
"""

import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.models.schemas import (
    EmbeddingResponse, EmbeddingStatsResponse, EmbeddingTestRequest, 
    EmbeddingTestResponse, ChunkEmbeddingResponse, ChunkResponse,
    SearchResultChunk
)
from app.services.vector_store import VectorStore
from app.services.embedding_service import EmbeddingService
from app.services.document_processor import DocumentService

router = APIRouter()


@router.get("/stats", response_model=EmbeddingStatsResponse)
async def get_embedding_stats():
    """
    Get statistics about embeddings in the vector store.
    
    Returns:
        EmbeddingStatsResponse: Comprehensive embedding statistics
    """
    try:
        vector_store = VectorStore()
        embedding_service = EmbeddingService()
        
        stats = vector_store.get_embedding_stats()
        
        return EmbeddingStatsResponse(
            total_embeddings=stats['total_embeddings'],
            embedding_dimension=stats['embedding_dimension'],
            model_name=embedding_service.model_name,
            average_magnitude=stats['average_magnitude'],
            min_magnitude=stats['min_magnitude'],
            max_magnitude=stats['max_magnitude'],
            sample_embedding_ids=stats['sample_embedding_ids']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get embedding stats: {str(e)}")


@router.get("/", response_model=List[EmbeddingResponse])
async def list_embeddings(
    limit: int = Query(default=10, ge=1, le=50, description="Number of embeddings to return"),
    include_text: bool = Query(default=True, description="Include text preview"),
    vector_ids: Optional[str] = Query(default=None, description="Comma-separated list of specific vector IDs")
):
    """
    Get a list of embeddings from the vector store.
    
    Args:
        limit: Maximum number of embeddings to return
        include_text: Whether to include text preview
        vector_ids: Optional comma-separated list of specific vector IDs
        
    Returns:
        List[EmbeddingResponse]: List of embedding data
    """
    try:
        vector_store = VectorStore()
        
        # Parse vector IDs if provided
        ids = None
        if vector_ids:
            ids = [id.strip() for id in vector_ids.split(',') if id.strip()]
        
        embeddings_data = vector_store.get_embeddings(
            ids=ids,
            limit=limit,
            include_text=include_text
        )
        
        return [
            EmbeddingResponse(
                vector_id=data['vector_id'],
                embedding=data['embedding'],
                dimension=data['dimension'],
                magnitude=data['magnitude'],
                text_preview=data.get('text_preview', ''),
                metadata=data['metadata']
            )
            for data in embeddings_data
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get embeddings: {str(e)}")


@router.get("/{vector_id}", response_model=EmbeddingResponse)
async def get_embedding(vector_id: str):
    """
    Get a specific embedding by vector ID.
    
    Args:
        vector_id: The vector ID in ChromaDB
        
    Returns:
        EmbeddingResponse: Embedding data
        
    Raises:
        HTTPException: If embedding not found
    """
    try:
        vector_store = VectorStore()
        
        embedding_data = vector_store.get_chunk_embedding(vector_id)
        
        if not embedding_data:
            raise HTTPException(status_code=404, detail="Embedding not found")
        
        return EmbeddingResponse(
            vector_id=embedding_data['vector_id'],
            embedding=embedding_data['embedding'],
            dimension=embedding_data['dimension'],
            magnitude=embedding_data['magnitude'],
            text_preview=embedding_data['text_preview'],
            metadata=embedding_data['metadata']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get embedding: {str(e)}")


@router.post("/test", response_model=EmbeddingTestResponse)
async def test_embedding_generation(request: EmbeddingTestRequest):
    """
    Test embedding generation with custom text.
    
    Args:
        request: Test request with text to embed
        
    Returns:
        EmbeddingTestResponse: Generated embedding and optional similarity results
    """
    try:
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        
        start_time = time.time()
        
        # Generate embedding for the test text
        embedding = embedding_service.generate_embedding(request.text)
        
        generation_time = time.time() - start_time
        
        # Calculate embedding magnitude
        magnitude = sum(x * x for x in embedding) ** 0.5
        
        # Optional similarity test against existing embeddings
        similar_chunks = None
        if request.include_similarity_test:
            try:
                search_results = vector_store.similarity_search(
                    query_embedding=embedding,
                    k=5,
                    min_similarity=0.1
                )
                
                similar_chunks = [
                    SearchResultChunk(
                        content=result['document'][:200] + "..." if len(result['document']) > 200 else result['document'],
                        similarity_score=result['similarity_score'],
                        metadata=result['metadata']
                    )
                    for result in search_results
                ]
            except Exception as e:
                print(f"Warning: Could not perform similarity test: {e}")
        
        return EmbeddingTestResponse(
            text=request.text,
            embedding=embedding,
            dimension=len(embedding),
            magnitude=magnitude,
            generation_time_seconds=round(generation_time, 3),
            similar_chunks=similar_chunks
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test embedding generation: {str(e)}")


@router.get("/chunks/{chunk_id}/embedding", response_model=ChunkEmbeddingResponse)
async def get_chunk_with_embedding(
    chunk_id: int,
    db: Session = Depends(get_database)
):
    """
    Get a chunk's data along with its embedding.
    
    Args:
        chunk_id: Database chunk ID
        db: Database session
        
    Returns:
        ChunkEmbeddingResponse: Chunk data with embedding information
        
    Raises:
        HTTPException: If chunk not found
    """
    try:
        document_service = DocumentService(db)
        vector_store = VectorStore()
        
        # Get chunk from database
        chunk = document_service.get_chunk(chunk_id)
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Get embedding from vector store if vector_id exists
        embedding_data = None
        if chunk.vector_id:
            embedding_data = vector_store.get_chunk_embedding(chunk.vector_id)
        
        return ChunkEmbeddingResponse(
            chunk=ChunkResponse.model_validate(chunk),
            embedding=embedding_data['embedding'] if embedding_data else None,
            embedding_stats=embedding_data['embedding_stats'] if embedding_data else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk with embedding: {str(e)}")


@router.get("/documents/{document_id}/embeddings", response_model=List[EmbeddingResponse])
async def get_document_embeddings(
    document_id: int,
    db: Session = Depends(get_database)
):
    """
    Get all embeddings for chunks belonging to a specific document.
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        List[EmbeddingResponse]: List of embeddings for the document's chunks
        
    Raises:
        HTTPException: If document not found
    """
    try:
        document_service = DocumentService(db)
        vector_store = VectorStore()
        
        # Check if document exists
        document = document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get all chunks for the document
        chunks = document_service.get_chunks_by_document(document_id)
        
        # Get vector IDs for chunks that have embeddings
        vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
        
        if not vector_ids:
            return []
        
        # Get embeddings from vector store
        embeddings_data = vector_store.get_embeddings(
            ids=vector_ids,
            include_text=True
        )
        
        return [
            EmbeddingResponse(
                vector_id=data['vector_id'],
                embedding=data['embedding'],
                dimension=data['dimension'],
                magnitude=data['magnitude'],
                text_preview=data['text_preview'],
                metadata=data['metadata']
            )
            for data in embeddings_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document embeddings: {str(e)}") 