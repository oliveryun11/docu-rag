#!/usr/bin/env python3
"""
Test script for RAG search functionality.
Demonstrates how to use the search service to query documents.
"""

import sys
import os
import asyncio

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.services.search_service import RAGSearchService


def test_rag_search():
    """Test the RAG search functionality with sample queries."""
    
    print("🔍 Testing RAG Search Functionality")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize search service
        search_service = RAGSearchService(db)
        
        # Test queries
        test_queries = [
            "How do I install Next.js?",
            "What is server-side rendering in Next.js?",
            "How to create dynamic routes?",
            "What are the benefits of using the App Router?",
            "How to deploy a Next.js application?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. Testing Query: '{query}'")
            print("-" * 40)
            
            try:
                # Perform RAG search
                result = search_service.search(
                    query=query,
                    k=3,  # Retrieve top 3 chunks
                    min_similarity=0.1
                )
                
                print(f"📊 Found {result['total_chunks']} relevant chunks")
                print(f"💬 Answer: {result['answer'][:200]}...")
                
                if result['sources']:
                    print(f"📚 Sources:")
                    for idx, source in enumerate(result['sources'][:2], 1):
                        print(f"   {idx}. {source['file_name']} (similarity: {source['similarity_score']:.3f})")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ RAG Search test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        
    finally:
        db.close()


def test_similarity_search():
    """Test similarity search without LLM generation."""
    
    print("\n🔍 Testing Similarity Search (No LLM)")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize search service
        search_service = RAGSearchService(db)
        
        query = "Next.js routing"
        
        print(f"Query: '{query}'")
        print("-" * 40)
        
        # Perform similarity search only
        result = search_service.similarity_search_only(
            query=query,
            k=5,
            min_similarity=0.1
        )
        
        print(f"📊 Found {result['total_chunks']} relevant chunks")
        
        if result['sources']:
            print(f"📚 Top Results:")
            for idx, source in enumerate(result['sources'][:3], 1):
                print(f"   {idx}. {source['file_name']} (similarity: {source['similarity_score']:.3f})")
                print(f"      Preview: {source['content_preview'][:100]}...")
                print()
        
        print("✅ Similarity search test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        
    finally:
        db.close()


def test_vector_store_connection():
    """Test vector store connection and basic operations."""
    
    print("\n🔗 Testing Vector Store Connection")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        search_service = RAGSearchService(db)
        vector_store = search_service.vector_store
        
        # Get collection info
        info = vector_store.get_collection_info()
        
        print(f"📦 Collection: {info['collection_name']}")
        print(f"📄 Documents: {info['document_count']}")
        print(f"💾 Storage: {info['storage_path']}")
        print(f"🔌 Status: {info['status']}")
        
        if info['document_count'] == 0:
            print("\n⚠️  No documents found in vector store.")
            print("   Please index some documents first using:")
            print("   python scripts/bulk_index_docs.py")
        
        print("✅ Vector store connection test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        
    finally:
        db.close()


def main():
    """Main function to run all tests."""
    
    print("🚀 RAG Search System Tests")
    print("=" * 60)
    
    # Test 1: Vector store connection
    test_vector_store_connection()
    
    # Test 2: Similarity search
    test_similarity_search()
    
    # Test 3: Full RAG search
    test_rag_search()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("\nTo use the RAG search API:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Visit: http://localhost:8000/docs")
    print("3. Try the /api/v1/search/ endpoints")


if __name__ == "__main__":
    main() 