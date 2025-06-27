#!/usr/bin/env python3
"""
Database backup script for DocuRAG application.
Creates a backup of both SQLite database and ChromaDB vector store.
"""

import sys
import os
import shutil
import json
from datetime import datetime
from pathlib import Path
import zipfile

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.services.vector_store import VectorStore
from app.config.database import SessionLocal
from app.models.database import Document, DocumentChunk, ProcessingLog


def create_backup_directory(backup_name: str = None) -> Path:
    """Create a backup directory with timestamp."""
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"docu_rag_backup_{timestamp}"
    
    backup_dir = Path("backups") / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_sqlite_database(backup_dir: Path) -> bool:
    """Backup SQLite database file."""
    print("📁 Backing up SQLite database...")
    
    try:
        if settings.DATABASE_URL.startswith("sqlite:///"):
            # Extract database file path
            db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
            
            if db_path.exists():
                # Copy database file to backup directory
                backup_db_path = backup_dir / "docu_rag.db"
                shutil.copy2(db_path, backup_db_path)
                print(f"  ✅ SQLite database backed up: {backup_db_path}")
                return True
            else:
                print(f"  ⚠️  Database file not found: {db_path}")
                return False
        else:
            print("  ⚠️  Non-SQLite databases not supported for file backup")
            return False
            
    except Exception as e:
        print(f"  ❌ Error backing up SQLite database: {e}")
        return False


def backup_vector_store(backup_dir: Path) -> bool:
    """Backup ChromaDB vector store."""
    print("🔢 Backing up ChromaDB vector store...")
    
    try:
        chroma_path = Path(settings.CHROMA_DB_PATH)
        
        if chroma_path.exists():
            # Copy entire ChromaDB directory
            backup_chroma_path = backup_dir / "chroma_db"
            shutil.copytree(chroma_path, backup_chroma_path, dirs_exist_ok=True)
            print(f"  ✅ ChromaDB backed up: {backup_chroma_path}")
            return True
        else:
            print(f"  ⚠️  ChromaDB directory not found: {chroma_path}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error backing up ChromaDB: {e}")
        return False


def backup_uploaded_files(backup_dir: Path) -> bool:
    """Backup uploaded files directory."""
    print("📎 Backing up uploaded files...")
    
    try:
        upload_path = Path(settings.UPLOAD_DIR)
        
        if upload_path.exists():
            # Copy entire uploads directory
            backup_upload_path = backup_dir / "uploads"
            shutil.copytree(upload_path, backup_upload_path, dirs_exist_ok=True)
            print(f"  ✅ Uploads backed up: {backup_upload_path}")
            return True
        else:
            print(f"  ⚠️  Uploads directory not found: {upload_path}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error backing up uploads: {e}")
        return False


def export_database_stats(backup_dir: Path) -> bool:
    """Export database statistics and metadata."""
    print("📊 Exporting database statistics...")
    
    try:
        db = SessionLocal()
        
        # Count documents by status
        document_stats = {}
        documents = db.query(Document).all()
        
        for doc in documents:
            status = doc.status.value if hasattr(doc.status, 'value') else str(doc.status)
            document_stats[status] = document_stats.get(status, 0) + 1
        
        # Count chunks
        chunk_count = db.query(DocumentChunk).count()
        
        # Get vector store info
        try:
            vector_store = VectorStore()
            vector_info = vector_store.get_collection_info()
        except Exception:
            vector_info = {"error": "Failed to connect to vector store"}
        
        # Compile stats
        stats = {
            "backup_timestamp": datetime.now().isoformat(),
            "database_url": settings.DATABASE_URL,
            "chroma_db_path": settings.CHROMA_DB_PATH,
            "upload_dir": settings.UPLOAD_DIR,
            "total_documents": len(documents),
            "documents_by_status": document_stats,
            "total_chunks": chunk_count,
            "vector_store": vector_info,
            "settings": {
                "app_name": settings.APP_NAME,
                "app_version": settings.APP_VERSION,
                "gemini_model": settings.GEMINI_MODEL,
                "gemini_embedding_model": settings.GEMINI_EMBEDDING_MODEL,
                "chroma_collection_name": settings.CHROMA_COLLECTION_NAME,
            }
        }
        
        # Save stats to JSON file
        stats_file = backup_dir / "backup_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"  ✅ Statistics exported: {stats_file}")
        print(f"     - {len(documents)} documents")
        print(f"     - {chunk_count} chunks")
        print(f"     - Vector store: {vector_info.get('document_count', 'unknown')} vectors")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error exporting statistics: {e}")
        return False
    finally:
        db.close()


def create_backup_archive(backup_dir: Path, compress: bool = True) -> bool:
    """Create a compressed archive of the backup."""
    if not compress:
        return True
    
    print("🗜️  Creating compressed backup archive...")
    
    try:
        archive_path = backup_dir.parent / f"{backup_dir.name}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in backup_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(backup_dir.parent)
                    zipf.write(file_path, arcname)
        
        # Remove uncompressed directory
        shutil.rmtree(backup_dir)
        
        print(f"  ✅ Backup archived: {archive_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating archive: {e}")
        return False


def main():
    """Main backup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup DocuRAG database and storage")
    parser.add_argument(
        "--name",
        type=str,
        help="Custom backup name (default: timestamp)"
    )
    parser.add_argument(
        "--no-files",
        action="store_true",
        help="Skip backing up uploaded files"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't create compressed archive"
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only backup database (skip vector store and files)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("DOCURAG DATABASE BACKUP")
    print("="*60)
    
    # Create backup directory
    backup_dir = create_backup_directory(args.name)
    print(f"📁 Backup directory: {backup_dir}")
    
    success = True
    
    # Backup SQLite database
    if not backup_sqlite_database(backup_dir):
        success = False
    
    # Backup vector store (unless db-only)
    if not args.db_only:
        if not backup_vector_store(backup_dir):
            success = False
    
    # Backup uploaded files (unless no-files or db-only)
    if not args.no_files and not args.db_only:
        if not backup_uploaded_files(backup_dir):
            success = False
    
    # Export statistics
    if not export_database_stats(backup_dir):
        success = False
    
    # Create archive (unless no-compress)
    if not args.no_compress:
        if not create_backup_archive(backup_dir, compress=True):
            success = False
    
    print("\n" + "="*60)
    if success:
        print("✅ BACKUP COMPLETED SUCCESSFULLY!")
        if not args.no_compress:
            print(f"📦 Backup archive: {backup_dir.parent}/{backup_dir.name}.zip")
        else:
            print(f"📁 Backup directory: {backup_dir}")
    else:
        print("❌ BACKUP COMPLETED WITH ERRORS!")
        print("Please check the error messages above.")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 