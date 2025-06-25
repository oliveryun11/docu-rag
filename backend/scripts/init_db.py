#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables for the DocuRAG application.
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import create_tables
from app.models.database import Document, DocumentChunk, ProcessingLog

def main():
    """Initialize the database with all tables."""
    print("Creating database tables...")
    
    try:
        create_tables()
        print("✅ Database tables created successfully!")
        print("Tables created:")
        print("  - documents")
        print("  - document_chunks") 
        print("  - processing_logs")
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 