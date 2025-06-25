"""
Vector store service using ChromaDB for storing and retrieving embeddings.
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from app.config.settings import settings


class VectorStore:
    """ChromaDB vector store for document embeddings."""
    
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # We'll use our own embedding function (Gemini) rather than ChromaDB's default
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self.collection = None
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize or get the document collection."""
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            print(f"Loaded existing ChromaDB collection: {self.collection_name}")
            
        except Exception:
            # Create new collection if it doesn't exist
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Document chunks for RAG"}
            )
            print(f"Created new ChromaDB collection: {self.collection_name}")
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata to ensure compatibility with ChromaDB.
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Dict[str, Any]: Cleaned metadata dictionary
        """
        cleaned = {}
        for key, value in metadata.items():
            # Skip None values
            if value is None:
                continue
            
            # Convert all values to strings to ensure compatibility
            if isinstance(value, (str, int, float, bool)):
                cleaned[str(key)] = str(value)
            elif isinstance(value, dict):
                # For nested dicts, convert to JSON string
                cleaned[str(key)] = str(value)
            elif isinstance(value, list):
                # For lists, convert to comma-separated string
                cleaned[str(key)] = ", ".join(str(item) for item in value if item is not None)
            else:
                # For other types, convert to string
                cleaned[str(key)] = str(value)
        
        return cleaned

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            texts: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            ids: Optional list of document IDs (will generate if not provided)
            
        Returns:
            List[str]: Document IDs that were added
            
        Raises:
            Exception: If adding documents fails
        """
        if not texts or not embeddings or not metadatas:
            raise ValueError("texts, embeddings, and metadatas cannot be empty")
        
        if len(texts) != len(embeddings) or len(texts) != len(metadatas):
            raise ValueError("texts, embeddings, and metadatas must have the same length")
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Clean metadatas to ensure ChromaDB compatibility
        cleaned_metadatas = [self._clean_metadata(metadata) for metadata in metadatas]
        
        try:
            # Add documents to ChromaDB
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=cleaned_metadatas,
                ids=ids
            )
            
            print(f"Added {len(texts)} documents to ChromaDB")
            return ids
            
        except Exception as e:
            raise Exception(f"Failed to add documents to vector store: {str(e)}")
    
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using embedding.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            where: Optional metadata filter
            min_similarity: Minimum similarity threshold
            
        Returns:
            List[Dict[str, Any]]: Search results with documents, scores, and metadata
        """
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert ChromaDB results to our format
            search_results = []
            
            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                distances = results['distances'][0] if results['distances'] else []
                
                for i, doc in enumerate(documents):
                    # Convert distance to similarity score (ChromaDB uses L2 distance)
                    distance = distances[i] if i < len(distances) else 1.0
                    similarity = max(0.0, 1.0 - (distance / 2.0))  # Rough conversion
                    
                    # Filter by minimum similarity
                    if similarity >= min_similarity:
                        result = {
                            'document': doc,
                            'similarity_score': similarity,
                            'distance': distance,
                            'metadata': metadatas[i] if i < len(metadatas) else {}
                        }
                        search_results.append(result)
            
            return search_results
            
        except Exception as e:
            raise Exception(f"Failed to search vector store: {str(e)}")
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Optional[Dict[str, Any]]: Document data if found, None otherwise
        """
        try:
            results = self.collection.get(
                ids=[document_id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            if (results['documents'] is not None and 
                len(results['documents']) > 0 and 
                results['documents'][0] is not None):
                return {
                    'id': document_id,
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0] if (results['metadatas'] and len(results['metadatas']) > 0) else {},
                    'embedding': results['embeddings'][0] if (results['embeddings'] and len(results['embeddings']) > 0) else None
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to get document {document_id}: {str(e)}")
            return None
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not ids:
                print("No IDs provided for deletion")
                return True
            
            print(f"Attempting to delete {len(ids)} documents from ChromaDB: {ids}")
            
            # Check if documents exist before deletion
            for doc_id in ids:
                try:
                    result = self.collection.get(ids=[doc_id])
                    exists = result['documents'] and result['documents'][0]
                    print(f"  Document {doc_id} exists before deletion: {bool(exists)}")
                except Exception as e:
                    print(f"  Error checking document {doc_id}: {e}")
            
            # Perform deletion
            self.collection.delete(ids=ids)
            print(f"ChromaDB delete operation completed for {len(ids)} documents")
            
            # Verify deletion
            for doc_id in ids:
                try:
                    result = self.collection.get(ids=[doc_id])
                    exists = result['documents'] and result['documents'][0]
                    print(f"  Document {doc_id} exists after deletion: {bool(exists)}")
                except Exception as e:
                    print(f"  Error verifying deletion of {doc_id}: {e}")
            
            return True
            
        except Exception as e:
            print(f"Failed to delete documents: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def delete_by_metadata(self, where: Dict[str, Any]) -> bool:
        """
        Delete documents by metadata filter.
        
        Args:
            where: Metadata filter conditions
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.collection.delete(where=where)
            print(f"Deleted documents matching filter: {where}")
            return True
            
        except Exception as e:
            print(f"Failed to delete documents by metadata: {str(e)}")
            return False
    
    def count_documents(self) -> int:
        """
        Get total number of documents in the collection.
        
        Returns:
            int: Number of documents
        """
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Failed to count documents: {str(e)}")
            return 0
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Dict[str, Any]: Collection information
        """
        return {
            "collection_name": self.collection_name,
            "document_count": self.count_documents(),
            "storage_path": settings.CHROMA_DB_PATH,
            "status": "connected" if self.collection else "disconnected"
        }
    
    def reset_collection(self) -> bool:
        """
        Reset (clear) the entire collection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self._initialize_collection()
            print(f"Reset collection: {self.collection_name}")
            return True
            
        except Exception as e:
            print(f"Failed to reset collection: {str(e)}")
            return False
    
    def search_by_text(
        self,
        query_text: str,
        k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using text query (requires embedding generation).
        Note: This is a convenience method that requires an embedding service.
        
        Args:
            query_text: Text query
            k: Number of results
            where: Optional metadata filter
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        # This method would require the embedding service
        # For now, we'll raise an error suggesting to use similarity_search with embeddings
        raise NotImplementedError(
            "Use similarity_search() with pre-generated query embeddings. "
            "Generate query embedding using EmbeddingService.generate_query_embedding()"
        )

    def get_embeddings(
        self,
        ids: Optional[List[str]] = None,
        limit: int = 10,
        include_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings from the vector store.
        
        Args:
            ids: Optional list of specific IDs to retrieve
            limit: Maximum number of embeddings to return (if ids not specified)
            include_text: Whether to include the document text
            
        Returns:
            List[Dict[str, Any]]: List of embeddings with metadata
        """
        try:
            if ids:
                # Get specific embeddings by ID
                results = self.collection.get(
                    ids=ids,
                    include=["embeddings", "documents", "metadatas"]
                )
            else:
                # Get all embeddings (limited)
                results = self.collection.get(
                    limit=limit,
                    include=["embeddings", "documents", "metadatas"]
                )
            
            embeddings_data = []
            
            # Check if we have embeddings and they contain data
            if results['embeddings'] is not None and len(results['embeddings']) > 0:
                for i, embedding in enumerate(results['embeddings']):
                    embedding_id = results['ids'][i] if results['ids'] and i < len(results['ids']) else f"unknown_{i}"
                    document = results['documents'][i] if results['documents'] and i < len(results['documents']) else ""
                    metadata = results['metadatas'][i] if results['metadatas'] and i < len(results['metadatas']) else {}
                    
                    # Calculate embedding magnitude
                    magnitude = sum(x * x for x in embedding) ** 0.5
                    
                    embedding_data = {
                        'vector_id': embedding_id,
                        'embedding': embedding,
                        'dimension': len(embedding),
                        'magnitude': magnitude,
                        'metadata': metadata
                    }
                    
                    if include_text:
                        # Truncate text for preview
                        text_preview = document[:200] + "..." if len(document) > 200 else document
                        embedding_data['text_preview'] = text_preview
                        embedding_data['full_text'] = document
                    
                    embeddings_data.append(embedding_data)
            
            return embeddings_data
            
        except Exception as e:
            raise Exception(f"Failed to get embeddings: {str(e)}")
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """
        Get statistics about embeddings in the vector store.
        
        Returns:
            Dict[str, Any]: Embedding statistics
        """
        try:
            # Get a sample of embeddings to calculate stats
            sample_size = min(100, self.count_documents())
            
            if sample_size == 0:
                return {
                    'total_embeddings': 0,
                    'embedding_dimension': 0,
                    'average_magnitude': 0.0,
                    'min_magnitude': 0.0,
                    'max_magnitude': 0.0,
                    'sample_embedding_ids': []
                }
            
            results = self.collection.get(
                limit=sample_size,
                include=["embeddings"]
            )
            
            if results['embeddings'] is None or len(results['embeddings']) == 0:
                return {
                    'total_embeddings': 0,
                    'embedding_dimension': 0,
                    'average_magnitude': 0.0,
                    'min_magnitude': 0.0,
                    'max_magnitude': 0.0,
                    'sample_embedding_ids': []
                }
            
            embeddings = results['embeddings']
            magnitudes = []
            
            for embedding in embeddings:
                magnitude = sum(x * x for x in embedding) ** 0.5
                magnitudes.append(magnitude)
            
            total_count = self.count_documents()
            dimension = len(embeddings[0]) if len(embeddings) > 0 else 0
            
            return {
                'total_embeddings': total_count,
                'embedding_dimension': dimension,
                'average_magnitude': sum(magnitudes) / len(magnitudes),
                'min_magnitude': min(magnitudes),
                'max_magnitude': max(magnitudes),
                'sample_embedding_ids': results['ids'][:10]  # First 10 IDs as samples
            }
            
        except Exception as e:
            raise Exception(f"Failed to get embedding stats: {str(e)}")
    
    def get_chunk_embedding(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk's embedding by vector ID.
        
        Args:
            vector_id: The vector ID in ChromaDB
            
        Returns:
            Optional[Dict[str, Any]]: Embedding data if found
        """
        try:
            results = self.collection.get(
                ids=[vector_id],
                include=["embeddings", "documents", "metadatas"]
            )
            
            if (results['embeddings'] is None or 
                len(results['embeddings']) == 0 or 
                results['embeddings'][0] is None):
                return None
            
            embedding = results['embeddings'][0]
            document = results['documents'][0] if results['documents'] else ""
            metadata = results['metadatas'][0] if results['metadatas'] else {}
            
            # Calculate embedding statistics
            magnitude = sum(x * x for x in embedding) ** 0.5
            
            return {
                'vector_id': vector_id,
                'embedding': embedding,
                'dimension': len(embedding),
                'magnitude': magnitude,
                'text_preview': document[:200] + "..." if len(document) > 200 else document,
                'full_text': document,
                'metadata': metadata,
                'embedding_stats': {
                    'magnitude': magnitude,
                    'min_value': min(embedding),
                    'max_value': max(embedding),
                    'mean_value': sum(embedding) / len(embedding),
                    'non_zero_count': sum(1 for x in embedding if x != 0.0)
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to get chunk embedding: {str(e)}") 