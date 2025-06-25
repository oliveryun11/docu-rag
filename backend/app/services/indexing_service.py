"""
Document indexing service that orchestrates the full processing pipeline.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.database import Document, DocumentChunk, ProcessingLog
from app.models.enums import DocumentStatus, FileType, ChunkStatus, ProcessingStage
from app.utils.text_processing import DocumentProcessor
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.services.document_processor import DocumentService


class IndexingService:
    """Service that orchestrates document processing, embedding, and indexing."""
    
    def __init__(self, db: Session):
        """
        Initialize the indexing service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.document_service = DocumentService(db)
        self.text_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
    
    def process_document(self, document_id: int) -> bool:
        """
        Process a document through the complete indexing pipeline.
        
        Args:
            document_id: ID of document to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        document = self.document_service.get_document(document_id)
        if not document:
            return False
        
        # Update status to processing
        self._update_document_status(
            document_id, 
            DocumentStatus.PROCESSING, 
            ProcessingStage.EXTRACTION
        )
        
        try:
            # Step 1: Extract and chunk text
            chunks_data, doc_metadata = self._extract_and_chunk(document)
            
            # Step 2: Generate embeddings
            embeddings = self._generate_embeddings(document_id, chunks_data)
            
            # Step 3: Store in vector database
            vector_ids = self._store_in_vector_db(document_id, chunks_data, embeddings)
            
            # Step 4: Save chunks to database
            self._save_chunks_to_db(document_id, chunks_data, embeddings, vector_ids)
            
            # Step 5: Update document metadata and status
            self._finalize_document(document_id, doc_metadata)
            
            self._log_processing_step(
                document_id, 
                ProcessingStage.COMPLETE, 
                "success", 
                f"Successfully processed document with {len(chunks_data)} chunks"
            )
            
            return True
            
        except Exception as e:
            # Handle processing failure
            self._handle_processing_error(document_id, str(e))
            return False
    
    def _extract_and_chunk(self, document: Document) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract text and chunk the document.
        
        Args:
            document: Document to process
            
        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: (chunks_data, doc_metadata)
        """
        start_time = time.time()
        
        try:
            self._log_processing_step(
                document.id,
                ProcessingStage.EXTRACTION,
                "info",
                f"Starting text extraction for {document.file_type} file"
            )
            
            # Convert string enum to FileType enum
            file_type = FileType(document.file_type)
            
            # Process document with LangChain
            chunks_data, doc_metadata = self.text_processor.process_document(
                document.file_path,
                file_type
            )
            
            duration = time.time() - start_time
            
            self._log_processing_step(
                document.id,
                ProcessingStage.CHUNKING,
                "success",
                f"Extracted {len(chunks_data)} chunks in {duration:.2f}s",
                {"duration_seconds": duration, "chunk_count": len(chunks_data)}
            )
            
            return chunks_data, doc_metadata
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_processing_step(
                document.id,
                ProcessingStage.EXTRACTION,
                "error",
                f"Text extraction failed: {str(e)}",
                {"duration_seconds": duration}
            )
            raise Exception(f"Text extraction failed: {str(e)}")
    
    def _generate_embeddings(self, document_id: int, chunks_data: List[Dict[str, Any]]) -> List[List[float]]:
        """
        Generate embeddings for document chunks.
        
        Args:
            document_id: Document ID
            chunks_data: List of chunk data
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        start_time = time.time()
        
        try:
            self._log_processing_step(
                document_id,
                ProcessingStage.EMBEDDING,
                "info",
                f"Generating embeddings for {len(chunks_data)} chunks"
            )
            
            # Extract text content from chunks
            texts = [chunk['content'] for chunk in chunks_data]
            
            # Generate embeddings in batches
            embeddings = self.embedding_service.generate_embeddings_batch(
                texts, 
                batch_size=5  # Smaller batch for rate limiting
            )
            
            duration = time.time() - start_time
            
            self._log_processing_step(
                document_id,
                ProcessingStage.EMBEDDING,
                "success",
                f"Generated {len(embeddings)} embeddings in {duration:.2f}s",
                {"duration_seconds": duration, "embedding_count": len(embeddings)}
            )
            
            return embeddings
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_processing_step(
                document_id,
                ProcessingStage.EMBEDDING,
                "error",
                f"Embedding generation failed: {str(e)}",
                {"duration_seconds": duration}
            )
            raise Exception(f"Embedding generation failed: {str(e)}")
    
    def _store_in_vector_db(
        self, 
        document_id: int, 
        chunks_data: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> List[str]:
        """
        Store chunks and embeddings in ChromaDB.
        
        Args:
            document_id: Document ID
            chunks_data: List of chunk data
            embeddings: List of embedding vectors
            
        Returns:
            List[str]: Vector database IDs
        """
        start_time = time.time()
        
        try:
            self._log_processing_step(
                document_id,
                ProcessingStage.INDEXING,
                "info",
                f"Storing {len(chunks_data)} chunks in vector database"
            )
            
            # Prepare data for ChromaDB
            texts = [chunk['content'] for chunk in chunks_data]
            metadatas = []
            
            # Get document info for consistent metadata
            document = self.document_service.get_document(document_id)
            doc_file_name = document.original_filename if document else "unknown"
            doc_file_type = document.file_type if document else "unknown"
            
            for i, chunk in enumerate(chunks_data):
                metadata = {
                    'document_id': document_id,
                    'chunk_index': chunk['chunk_index'],
                    'character_count': chunk['character_count'],
                    'word_count': chunk['word_count'],
                    'start_page': chunk.get('start_page'),
                    'end_page': chunk.get('end_page'),
                    'file_name': chunk['metadata'].get('file_name') or doc_file_name,
                    'file_type': chunk['metadata'].get('file_type') or doc_file_type
                }
                metadatas.append(metadata)
            
            # Store in ChromaDB
            vector_ids = self.vector_store.add_documents(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            duration = time.time() - start_time
            
            self._log_processing_step(
                document_id,
                ProcessingStage.INDEXING,
                "success",
                f"Stored {len(vector_ids)} chunks in vector database in {duration:.2f}s",
                {"duration_seconds": duration, "vector_count": len(vector_ids)}
            )
            
            return vector_ids
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_processing_step(
                document_id,
                ProcessingStage.INDEXING,
                "error",
                f"Vector storage failed: {str(e)}",
                {"duration_seconds": duration}
            )
            raise Exception(f"Vector storage failed: {str(e)}")
    
    def _save_chunks_to_db(
        self,
        document_id: int,
        chunks_data: List[Dict[str, Any]],
        embeddings: List[List[float]],
        vector_ids: List[str]
    ):
        """
        Save document chunks to the database.
        
        Args:
            document_id: Document ID
            chunks_data: List of chunk data
            embeddings: List of embedding vectors
            vector_ids: List of vector database IDs
        """
        try:
            # Create DocumentChunk records
            chunk_records = []
            
            for i, (chunk_data, vector_id) in enumerate(zip(chunks_data, vector_ids)):
                chunk_record = DocumentChunk(
                    document_id=document_id,
                    content=chunk_data['content'],
                    chunk_index=chunk_data['chunk_index'],
                    character_count=chunk_data['character_count'],
                    word_count=chunk_data['word_count'],
                    start_page=chunk_data.get('start_page'),
                    end_page=chunk_data.get('end_page'),
                    status=ChunkStatus.EMBEDDED.value,
                    vector_id=vector_id,
                    embedding_model=self.embedding_service.model_name,
                    embedded_at=datetime.utcnow()
                )
                chunk_records.append(chunk_record)
            
            # Bulk insert chunks
            self.db.add_all(chunk_records)
            self.db.commit()
            
            self._log_processing_step(
                document_id,
                ProcessingStage.COMPLETE,
                "success",
                f"Saved {len(chunk_records)} chunks to database"
            )
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to save chunks to database: {str(e)}")
    
    def _finalize_document(self, document_id: int, doc_metadata: Dict[str, Any]):
        """
        Update document with final metadata and status.
        
        Args:
            document_id: Document ID
            doc_metadata: Document metadata
        """
        try:
            document = self.document_service.get_document(document_id)
            if document:
                # Update document metadata
                document.word_count = doc_metadata.get('word_count')
                document.character_count = doc_metadata.get('character_count')
                document.page_count = doc_metadata.get('page_count')
                document.status = DocumentStatus.INDEXED.value
                document.processing_stage = ProcessingStage.COMPLETE.value
                document.processed_at = datetime.utcnow()
                document.error_message = None  # Clear any previous errors
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to finalize document: {str(e)}")
    
    def _update_document_status(
        self, 
        document_id: int, 
        status: DocumentStatus, 
        stage: Optional[ProcessingStage] = None
    ):
        """
        Update document processing status.
        
        Args:
            document_id: Document ID
            status: New status
            stage: Current processing stage
        """
        try:
            document = self.document_service.get_document(document_id)
            if document:
                document.status = status.value
                if stage:
                    document.processing_stage = stage.value
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            print(f"Failed to update document status: {str(e)}")
    
    def _handle_processing_error(self, document_id: int, error_message: str):
        """
        Handle processing errors by updating document status and logging.
        
        Args:
            document_id: Document ID
            error_message: Error message
        """
        try:
            # Update document status to failed
            document = self.document_service.get_document(document_id)
            if document:
                document.status = DocumentStatus.FAILED.value
                document.error_message = error_message
                self.db.commit()
            
            # Log the error
            self._log_processing_step(
                document_id,
                ProcessingStage.COMPLETE,
                "error",
                f"Document processing failed: {error_message}"
            )
            
        except Exception as e:
            self.db.rollback()
            print(f"Failed to handle processing error: {str(e)}")
    
    def _log_processing_step(
        self,
        document_id: int,
        stage: ProcessingStage,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a processing step to the database.
        
        Args:
            document_id: Document ID
            stage: Processing stage
            status: Step status (success, error, info, warning)
            message: Log message
            details: Optional additional details
        """
        try:
            log_entry = ProcessingLog(
                document_id=document_id,
                stage=stage.value,
                status=status,
                message=message,
                details=details
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            print(f"Failed to log processing step: {str(e)}")
    
    def get_processing_status(self, document_id: int) -> Dict[str, Any]:
        """
        Get detailed processing status for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dict[str, Any]: Processing status information
        """
        document = self.document_service.get_document(document_id)
        if not document:
            return {"error": "Document not found"}
        
        # Get processing logs
        logs = self.db.query(ProcessingLog).filter(
            ProcessingLog.document_id == document_id
        ).order_by(ProcessingLog.created_at.desc()).limit(10).all()
        
        # Get chunk count
        chunk_count = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).count()
        
        return {
            "document_id": document_id,
            "status": document.status,
            "processing_stage": document.processing_stage,
            "error_message": document.error_message,
            "chunk_count": chunk_count,
            "processed_at": document.processed_at,
            "recent_logs": [
                {
                    "stage": log.stage,
                    "status": log.status,
                    "message": log.message,
                    "created_at": log.created_at,
                    "details": log.details
                }
                for log in logs
            ]
        }
    
    def reprocess_document(self, document_id: int) -> bool:
        """
        Reprocess a document (useful for failed documents or updates).
        
        Args:
            document_id: Document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clean up existing chunks and vector data
            self._cleanup_document_data(document_id)
            
            # Reset document status
            self._update_document_status(document_id, DocumentStatus.UPLOADED)
            
            # Process again
            return self.process_document(document_id)
            
        except Exception as e:
            self._handle_processing_error(document_id, f"Reprocessing failed: {str(e)}")
            return False
    
    def _cleanup_document_data(self, document_id: int):
        """
        Clean up existing chunks and vector data for a document.
        
        Args:
            document_id: Document ID
        """
        try:
            print(f"Starting cleanup for document {document_id}")
            
            # Get existing chunks to get vector IDs
            chunks = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            print(f"Found {len(chunks)} chunks for document {document_id}")
            
            # Delete from vector store
            if chunks:
                vector_ids = [chunk.vector_id for chunk in chunks if chunk.vector_id]
                print(f"Vector IDs to delete: {vector_ids}")
                
                if vector_ids:
                    success = self.vector_store.delete_documents(vector_ids)
                    print(f"Vector deletion success: {success}")
                else:
                    print("No vector IDs found in chunks")
            else:
                print("No chunks found for document")
            
            # Delete chunks from database
            chunks_deleted = self.db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            print(f"Deleted {chunks_deleted} chunks from database")
            
            # Delete processing logs
            logs_deleted = self.db.query(ProcessingLog).filter(
                ProcessingLog.document_id == document_id
            ).delete()
            print(f"Deleted {logs_deleted} processing logs")
            
            self.db.commit()
            print(f"Cleanup completed for document {document_id}")
            
        except Exception as e:
            self.db.rollback()
            print(f"Failed to cleanup document data: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system processing status.
        
        Returns:
            Dict[str, Any]: System status information
        """
        try:
            # Document counts by status
            status_counts = {}
            for status in DocumentStatus:
                count = self.db.query(Document).filter(
                    Document.status == status.value
                ).count()
                status_counts[status.value] = count
            
            # Vector store info
            vector_info = self.vector_store.get_collection_info()
            
            # Embedding service info
            embedding_info = self.embedding_service.get_model_info()
            
            return {
                "documents_by_status": status_counts,
                "vector_store": vector_info,
                "embedding_service": embedding_info,
                "services_connected": {
                    "database": True,
                    "vector_store": vector_info["status"] == "connected",
                    "embedding_api": embedding_info["api_configured"]
                }
            }
            
        except Exception as e:
            return {"error": f"Failed to get system status: {str(e)}"} 