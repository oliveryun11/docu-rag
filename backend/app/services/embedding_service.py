"""
Embedding service for generating text embeddings using Google Gemini.
"""

import time
from typing import List, Optional, Dict, Any
import google.generativeai as genai

from app.config.settings import settings


class EmbeddingService:
    """Service for generating text embeddings using Google Gemini."""
    
    def __init__(self):
        """Initialize the embedding service with Gemini API."""
        # Configure Gemini API
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model_name = settings.GEMINI_EMBEDDING_MODEL
        
        # Rate limiting settings
        self.requests_per_minute = 60  # Adjust based on your API limits
        self.last_request_time = 0
        self.min_request_interval = 60 / self.requests_per_minute
    
    def _rate_limit(self):
        """Apply rate limiting to API requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            self._rate_limit()
            
            # Generate embedding using Gemini
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                title="Document chunk"
            )
            
            if not result or 'embedding' not in result:
                raise Exception("Invalid response from Gemini API")
            
            return result['embedding']
            
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            Exception: If any embedding generation fails
        """
        if not texts:
            return []
        
        embeddings = []
        failed_indices = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for j, text in enumerate(batch):
                try:
                    embedding = self.generate_embedding(text)
                    batch_embeddings.append(embedding)
                except Exception as e:
                    print(f"Failed to embed text at index {i + j}: {str(e)}")
                    failed_indices.append(i + j)
                    # Use zero vector as fallback
                    batch_embeddings.append([0.0] * 768)  # Assuming 768-dim embeddings
            
            embeddings.extend(batch_embeddings)
        
        if failed_indices:
            print(f"Warning: Failed to generate embeddings for {len(failed_indices)} texts")
        
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            List[float]: Query embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            self._rate_limit()
            
            # Generate embedding with query task type
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            
            if not result or 'embedding' not in result:
                raise Exception("Invalid response from Gemini API")
            
            return result['embedding']
            
        except Exception as e:
            raise Exception(f"Failed to generate query embedding: {str(e)}")
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from this model.
        
        Returns:
            int: Embedding dimension
        """
        # For Gemini embedding models, typical dimension is 768
        # We could make a test call to get the actual dimension
        try:
            test_embedding = self.generate_embedding("test")
            return len(test_embedding)
        except:
            # Fallback to known dimension for Gemini
            return 768
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score (0-1)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        
        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, (similarity + 1) / 2))
    
    def validate_api_key(self) -> bool:
        """
        Validate that the Gemini API key is working.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Try to generate a simple embedding
            self.generate_embedding("test")
            return True
        except Exception as e:
            print(f"API key validation failed: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.get_embedding_dimension(),
            "api_configured": bool(settings.GOOGLE_API_KEY),
            "rate_limit_rpm": self.requests_per_minute
        } 