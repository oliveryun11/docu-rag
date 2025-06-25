#!/usr/bin/env python3
"""
Test script to view and analyze embeddings.
"""

import sys
import os
import asyncio
import numpy as np
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.config.settings import settings


def print_embedding_analysis(embedding, text=""):
    """Print detailed analysis of an embedding vector."""
    embedding = np.array(embedding)
    
    print(f"\n{'='*60}")
    print(f"EMBEDDING ANALYSIS")
    print(f"{'='*60}")
    
    if text:
        print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        print("-" * 60)
    
    print(f"Dimension: {len(embedding)}")
    print(f"Magnitude (L2 norm): {np.linalg.norm(embedding):.6f}")
    print(f"Min value: {np.min(embedding):.6f}")
    print(f"Max value: {np.max(embedding):.6f}")
    print(f"Mean value: {np.mean(embedding):.6f}")
    print(f"Standard deviation: {np.std(embedding):.6f}")
    print(f"Non-zero values: {np.count_nonzero(embedding)}/{len(embedding)}")
    print(f"Sparsity: {(1 - np.count_nonzero(embedding)/len(embedding))*100:.2f}%")
    
    # Show first and last 10 values
    print(f"\nFirst 10 values: {embedding[:10]}")
    print(f"Last 10 values: {embedding[-10:]}")
    
    # Show histogram of value ranges
    positive_count = np.sum(embedding > 0)
    negative_count = np.sum(embedding < 0)
    zero_count = np.sum(embedding == 0)
    
    print(f"\nValue distribution:")
    print(f"  Positive values: {positive_count} ({positive_count/len(embedding)*100:.1f}%)")
    print(f"  Negative values: {negative_count} ({negative_count/len(embedding)*100:.1f}%)")
    print(f"  Zero values: {zero_count} ({zero_count/len(embedding)*100:.1f}%)")


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    vec1, vec2 = np.array(vec1), np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


async def test_embedding_generation():
    """Test embedding generation with sample texts."""
    print("Testing Embedding Generation")
    print("=" * 60)
    
    try:
        embedding_service = EmbeddingService()
        
        # Test texts with different characteristics
        test_texts = [
            "Machine learning is a subset of artificial intelligence.",
            "The quick brown fox jumps over the lazy dog.",
            "Next.js is a React framework for building web applications.",
            "Data science involves extracting insights from data.",
            "Python is a popular programming language for AI development."
        ]
        
        embeddings = []
        
        for i, text in enumerate(test_texts):
            print(f"\nGenerating embedding {i+1}/{len(test_texts)}...")
            print(f"Text: {text}")
            
            start_time = datetime.now()
            embedding = embedding_service.generate_embedding(text)
            generation_time = (datetime.now() - start_time).total_seconds()
            
            print(f"Generation time: {generation_time:.3f} seconds")
            print_embedding_analysis(embedding, text)
            
            embeddings.append((text, embedding))
        
        # Test similarity between embeddings
        print(f"\n{'='*60}")
        print("SIMILARITY ANALYSIS")
        print("=" * 60)
        
        for i in range(len(embeddings)):
            for j in range(i+1, len(embeddings)):
                text1, emb1 = embeddings[i]
                text2, emb2 = embeddings[j]
                similarity = cosine_similarity(emb1, emb2)
                
                print(f"\nSimilarity between texts {i+1} and {j+1}: {similarity:.4f}")
                print(f"Text 1: {text1[:50]}...")
                print(f"Text 2: {text2[:50]}...")
                
        return True
        
    except Exception as e:
        print(f"Error testing embedding generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store operations."""
    print("\n" + "="*60)
    print("TESTING VECTOR STORE")
    print("="*60)
    
    try:
        vector_store = VectorStore()
        
        # Get basic stats
        stats = vector_store.get_embedding_stats()
        print(f"Total embeddings in store: {stats['total_embeddings']}")
        print(f"Embedding dimension: {stats['embedding_dimension']}")
        print(f"Average magnitude: {stats['average_magnitude']:.6f}")
        print(f"Min magnitude: {stats['min_magnitude']:.6f}")
        print(f"Max magnitude: {stats['max_magnitude']:.6f}")
        
        if stats['total_embeddings'] > 0:
            print(f"Sample embedding IDs: {stats['sample_embedding_ids'][:5]}")
            
            # Get a few sample embeddings
            sample_embeddings = vector_store.get_embeddings(limit=3, include_text=True)
            
            for i, embedding_data in enumerate(sample_embeddings):
                print(f"\n--- Sample Embedding {i+1} ---")
                print(f"Vector ID: {embedding_data['vector_id']}")
                print(f"Text preview: {embedding_data['text_preview']}")
                print_embedding_analysis(embedding_data['embedding'])
        
        else:
            print("No embeddings found in vector store.")
            print("Try uploading and processing some documents first.")
        
        return True
        
    except Exception as e:
        print(f"Error testing vector store: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_api_connection():
    """Check if we can connect to the embedding service."""
    print("CHECKING API CONNECTION")
    print("="*60)
    
    try:
        embedding_service = EmbeddingService()
        
        # Test with a simple text
        test_text = "Hello world"
        embedding = embedding_service.generate_embedding(test_text)
        
        print(f"✓ Successfully connected to {embedding_service.model_name}")
        print(f"✓ Generated embedding with dimension: {len(embedding)}")
        print(f"✓ API is working correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Error connecting to embedding service: {e}")
        print(f"Check your GOOGLE_API_KEY in settings")
        return False


async def main():
    """Main test function."""
    print("EMBEDDING VERIFICATION TOOL")
    print("="*60)
    print(f"Embedding model: {settings.GEMINI_EMBEDDING_MODEL}")
    print(f"Vector store path: {settings.CHROMA_DB_PATH}")
    print()
    
    # Check API connection first
    if not check_api_connection():
        print("\n❌ Cannot connect to embedding service. Stopping tests.")
        return
    
    print("\n" + "✓ API connection successful!")
    
    # Test embedding generation
    print("\n" + "="*60)
    success = await test_embedding_generation()
    
    if success:
        print("\n" + "✓ Embedding generation tests passed!")
    else:
        print("\n" + "❌ Embedding generation tests failed!")
    
    # Test vector store
    success = test_vector_store()
    
    if success:
        print("\n" + "✓ Vector store tests passed!")
    else:
        print("\n" + "❌ Vector store tests failed!")
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\nTo view embeddings via API, start the server and visit:")
    print("  GET /api/v1/embeddings/stats - Get embedding statistics")
    print("  GET /api/v1/embeddings/ - List embeddings")
    print("  POST /api/v1/embeddings/test - Test embedding generation")


if __name__ == "__main__":
    asyncio.run(main()) 