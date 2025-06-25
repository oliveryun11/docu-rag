#!/usr/bin/env python3
"""
Debug script to check ChromaDB metadata storage.
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import VectorStore


def inspect_metadata():
    """Inspect ChromaDB metadata to debug the 'Unknown' file names."""
    
    print("🔍 Debugging ChromaDB Metadata")
    print("=" * 50)
    
    try:
        # Initialize vector store
        vector_store = VectorStore()
        
        # Get collection info
        info = vector_store.get_collection_info()
        print(f"📦 Collection: {info['collection_name']}")
        print(f"📄 Documents: {info['document_count']}")
        
        if info['document_count'] == 0:
            print("❌ No documents in collection!")
            return
        
        # Query a few random documents to inspect metadata
        print("\n🧐 Inspecting sample documents...")
        print("-" * 40)
        
        # Use vector store to get some sample documents
        # We'll do a dummy search to get some results
        try:
            # Try to get raw data from ChromaDB
            collection = vector_store.collection
            
            # Get first 5 documents with their metadata
            results = collection.get(
                limit=5,
                include=["documents", "metadatas"]
            )
            
            if results['documents']:
                for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
                    print(f"\n📄 Document {i+1}:")
                    print(f"   Content preview: {doc[:100]}...")
                    print(f"   Metadata keys: {list(metadata.keys()) if metadata else 'None'}")
                    
                    if metadata:
                        print(f"   document_id: {metadata.get('document_id', 'MISSING')}")
                        print(f"   file_name: {metadata.get('file_name', 'MISSING')}")
                        print(f"   file_type: {metadata.get('file_type', 'MISSING')}")
                        print(f"   chunk_index: {metadata.get('chunk_index', 'MISSING')}")
                    else:
                        print("   ❌ No metadata found!")
            else:
                print("❌ No documents found in results!")
                
        except Exception as e:
            print(f"❌ Error inspecting documents: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Diagnosis:")
        
        # Check if we can find the issue
        sample_metadata = results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else {}
        
        if not sample_metadata:
            print("❌ No metadata stored in ChromaDB at all!")
        elif 'file_name' not in sample_metadata:
            print("❌ file_name field missing from metadata!")
            print(f"   Available fields: {list(sample_metadata.keys())}")
        elif sample_metadata.get('file_name') is None:
            print("❌ file_name field is None!")
        elif sample_metadata.get('file_name') == '':
            print("❌ file_name field is empty string!")
        else:
            print(f"✅ file_name seems OK: {sample_metadata.get('file_name')}")
            print("   Issue might be elsewhere...")
        
    except Exception as e:
        print(f"❌ Failed to inspect metadata: {e}")


def main():
    """Main function."""
    inspect_metadata()


if __name__ == "__main__":
    main() 