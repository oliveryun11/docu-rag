"""
Document processor service for basic document management.
"""

import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, UploadFile

from app.models.database import Document, DocumentChunk
from app.models.schemas import DocumentCreate, DocumentUpdate, DocumentResponse
from app.models.enums import DocumentStatus, FileType
from app.utils.file_handlers import save_uploaded_file, delete_file, validate_file_type
from app.config.settings import settings


class DocumentService:
    """Service for document management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_document(self, file: UploadFile) -> Document:
        """
        Create a new document from uploaded file.
        
        Args:
            file: Uploaded file
            
        Returns:
            Document: Created document model
            
        Raises:
            HTTPException: If creation fails
        """
        try:
            # Save file to disk
            unique_filename, file_path, file_size = await save_uploaded_file(file)
            
            # Validate file type
            file_type = validate_file_type(file.filename)
            
            # Create document record
            document = Document(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_type=file_type.value,
                file_size=file_size,
                status=DocumentStatus.UPLOADED.value
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            return document
            
        except Exception as e:
            self.db.rollback()
            # Clean up file if database operation failed
            if 'file_path' in locals():
                delete_file(file_path)
            
            if isinstance(e, HTTPException):
                raise e
            # Log the full error for debugging
            import traceback
            print(f"Document creation error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """
        Get document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Optional[Document]: Document if found, None otherwise
        """
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_documents_by_ids(self, document_ids: List[int]) -> List[Document]:
        """
        Get multiple documents by their IDs in a single query.
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            List[Document]: List of documents found
        """
        if not document_ids:
            return []
        
        return self.db.query(Document).filter(Document.id.in_(document_ids)).all()
    
    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None,
        file_type: Optional[FileType] = None,
        search: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """
        Get paginated list of documents with optional filters.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by document status
            file_type: Filter by file type
            search: Search in filename or title
            
        Returns:
            tuple[List[Document], int]: (documents, total_count)
        """
        query = self.db.query(Document)
        
        # Apply filters
        if status:
            query = query.filter(Document.status == status.value)
        
        if file_type:
            query = query.filter(Document.file_type == file_type.value)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Document.filename.ilike(search_term)) |
                (Document.original_filename.ilike(search_term)) |
                (Document.title.ilike(search_term))
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and order
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        
        return documents, total
    
    def update_document(self, document_id: int, update_data: DocumentUpdate) -> Optional[Document]:
        """
        Update document metadata.
        
        Args:
            document_id: Document ID
            update_data: Update data
            
        Returns:
            Optional[Document]: Updated document if found, None otherwise
        """
        document = self.get_document(document_id)
        if not document:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(document, field, value)
        
        self.db.commit()
        self.db.refresh(document)
        
        return document
    
    def delete_document(self, document_id: int) -> bool:
        """
        Delete document and associated files.
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        document = self.get_document(document_id)
        if not document:
            return False
        
        try:
            # Import here to avoid circular imports
            from app.services.indexing_service import IndexingService
            
            # Clean up vector database entries first
            indexing_service = IndexingService(self.db)
            indexing_service._cleanup_document_data(document_id)
            
            # Delete physical file
            delete_file(document.file_path)
            
            # Delete database record (cascades to chunks)
            self.db.delete(document)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
    
    def get_document_chunks(self, document_id: int) -> List[DocumentChunk]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
    
    def get_chunk(self, chunk_id: int) -> Optional[DocumentChunk]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Optional[DocumentChunk]: Chunk if found, None otherwise
        """
        return self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
    
    def get_chunks_by_document(self, document_id: int) -> List[DocumentChunk]:
        """
        Get all chunks for a document (alias for get_document_chunks).
        
        Args:
            document_id: Document ID
            
        Returns:
            List[DocumentChunk]: List of document chunks
        """
        return self.get_document_chunks(document_id)
    
    def get_document_stats(self) -> Dict[str, Any]:
        """
        Get document statistics.
        
        Returns:
            Dict[str, Any]: Document statistics
        """
        total_documents = self.db.query(Document).count()
        
        # Documents by status
        status_counts = {}
        for status in DocumentStatus:
            count = self.db.query(Document).filter(Document.status == status.value).count()
            status_counts[status.value] = count
        
        # Documents by file type
        type_counts = {}
        for file_type in FileType:
            count = self.db.query(Document).filter(Document.file_type == file_type.value).count()
            type_counts[file_type.value] = count
        
        # Total chunks
        total_chunks = self.db.query(DocumentChunk).count()
        
        # Total file size
        total_size = self.db.query(func.sum(Document.file_size)).scalar() or 0
        
        return {
            "total_documents": total_documents,
            "documents_by_status": status_counts,
            "documents_by_type": type_counts,
            "total_chunks": total_chunks,
            "total_size_bytes": total_size
        }
    
    def update_document_status(self, document_id: int, status: DocumentStatus, error_message: Optional[str] = None) -> Optional[Document]:
        """
        Update document processing status.
        
        Args:
            document_id: Document ID
            status: New status
            error_message: Error message if status is FAILED
            
        Returns:
            Optional[Document]: Updated document if found, None otherwise
        """
        document = self.get_document(document_id)
        if not document:
            return None
        
        document.status = status.value
        if error_message:
            document.error_message = error_message
        
        self.db.commit()
        self.db.refresh(document)
        
        return document 