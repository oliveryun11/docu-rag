#!/usr/bin/env python3
"""
Database reset script for DocuRAG application.
Clears all data and resets the database to a clean state.
"""

import sys
import os
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import drop_tables, create_tables
from app.config.settings import settings
from app.services.vector_store import VectorStore


def reset_database():
    """Reset the database (with special handling for SQLite)."""
    print("🗑️  Resetting database...")
    
    try:
        # Check if it's a SQLite database
        if settings.DATABASE_URL.startswith("sqlite:///"):
            # Extract the database file path from the URL
            # Format: sqlite:///./docu_rag.db -> ./docu_rag.db
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            db_file = Path(db_path)
            
            if db_file.exists():
                # Delete the SQLite file directly (more reliable than DROP TABLE)
                db_file.unlink()
                print(f"  ✅ Deleted database file: {db_file}")
            else:
                print(f"  ℹ️  Database file doesn't exist: {db_file}")
            
            # Recreate all tables (this will create a new SQLite file)
            create_tables()
            print("  ✅ Recreated database tables")
            
        else:
            # For non-SQLite databases, use the table drop/create approach
            drop_tables()
            print("  ✅ Dropped all database tables")
            
            create_tables()
            print("  ✅ Recreated database tables")
        
    except Exception as e:
        print(f"  ❌ Error resetting database: {e}")
        return False
    
    return True


def reset_vector_store():
    """Reset the ChromaDB vector store."""
    print("🗑️  Resetting vector store...")
    
    try:
        vector_store = VectorStore()
        vector_store.reset_collection()
        print("  ✅ Reset ChromaDB collection")
        
    except Exception as e:
        print(f"  ❌ Error resetting vector store: {e}")
        return False
    
    return True


def reset_uploaded_files():
    """Reset uploaded files directory."""
    print("🗑️  Resetting uploaded files...")
    
    try:
        upload_dir = Path(settings.UPLOAD_DIR)
        
        if upload_dir.exists():
            # Remove the entire upload directory
            shutil.rmtree(upload_dir)
            print(f"  ✅ Removed upload directory: {upload_dir}")
            
        # Recreate the upload directory
        upload_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Recreated upload directory: {upload_dir}")
        
    except Exception as e:
        print(f"  ❌ Error resetting uploaded files: {e}")
        return False
    
    return True


def main():
    """Main function to reset everything."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset DocuRAG database and storage")
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep uploaded files (only reset database and vector store)"
    )
    parser.add_argument(
        "--db-only",
        action="store_true", 
        help="Only reset the database (keep vector store and files)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt
    if not args.confirm:
        print("⚠️  WARNING: This will delete ALL data from your DocuRAG application!")
        print("This includes:")
        print("  - All documents and chunks in the database")
        print("  - All vectors in ChromaDB")
        if not args.keep_files and not args.db_only:
            print("  - All uploaded files")
        print()
        
        confirm = input("Are you sure you want to proceed? (type 'yes' to confirm): ")
        if confirm.lower() != 'yes':
            print("Reset cancelled.")
            sys.exit(0)
    
    print("\n" + "="*60)
    print("RESETTING DOCURAG APPLICATION DATA")
    print("="*60)
    
    success = True
    
    # Reset database
    if not reset_database():
        success = False
    
    # Reset vector store (unless db-only)
    if not args.db_only:
        if not reset_vector_store():
            success = False
    
    # Reset uploaded files (unless keep-files or db-only)
    if not args.keep_files and not args.db_only:
        if not reset_uploaded_files():
            success = False
    
    print("\n" + "="*60)
    if success:
        print("✅ DATABASE RESET COMPLETED SUCCESSFULLY!")
        print("You can now run the bulk indexer with a clean slate.")
    else:
        print("❌ DATABASE RESET COMPLETED WITH ERRORS!")
        print("Please check the error messages above.")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 