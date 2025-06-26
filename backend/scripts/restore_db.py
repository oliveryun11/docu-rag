#!/usr/bin/env python3
"""
Database restore script for DocuRAG application.
Restores both SQLite database and ChromaDB vector store from backup.
"""

import sys
import os
import shutil
import json
from pathlib import Path
import zipfile
from datetime import datetime

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.services.vector_store import VectorStore


def list_available_backups() -> list:
    """List all available backups."""
    backups = []
    backup_base = Path("backups")
    
    if not backup_base.exists():
        return backups
    
    # Look for both directories and zip files
    for item in backup_base.iterdir():
        if item.is_dir():
            backups.append({
                "name": item.name,
                "path": item,
                "type": "directory",
                "size": sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            })
        elif item.suffix == ".zip":
            backups.append({
                "name": item.stem,
                "path": item,
                "type": "archive",
                "size": item.stat().st_size
            })
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x["path"].stat().st_mtime, reverse=True)
    return backups


def extract_backup_if_needed(backup_path: Path) -> Path:
    """Extract backup if it's a zip file."""
    if backup_path.suffix == ".zip":
        print(f"📦 Extracting backup archive: {backup_path}")
        
        # Create temporary extraction directory
        extract_dir = backup_path.parent / f"temp_{backup_path.stem}"
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(extract_dir)
        
        # Find the actual backup directory inside
        backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if backup_dirs:
            actual_backup_dir = backup_dirs[0]
            return actual_backup_dir
        else:
            return extract_dir
    
    return backup_path


def load_backup_stats(backup_dir: Path) -> dict:
    """Load backup statistics if available."""
    stats_file = backup_dir / "backup_stats.json"
    
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load backup stats: {e}")
    
    return {}


def restore_sqlite_database(backup_dir: Path) -> bool:
    """Restore SQLite database from backup."""
    print("📁 Restoring SQLite database...")
    
    try:
        backup_db_path = backup_dir / "docu_rag.db"
        
        if not backup_db_path.exists():
            print(f"  ⚠️  Backup database not found: {backup_db_path}")
            return False
        
        if settings.DATABASE_URL.startswith("sqlite:///"):
            # Extract current database file path
            current_db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
            
            # Backup current database if it exists
            if current_db_path.exists():
                backup_current_name = f"{current_db_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                current_db_path.rename(current_db_path.parent / backup_current_name)
                print(f"  📋 Current database backed up as: {backup_current_name}")
            
            # Restore from backup
            shutil.copy2(backup_db_path, current_db_path)
            print(f"  ✅ SQLite database restored: {current_db_path}")
            return True
        else:
            print("  ⚠️  Non-SQLite databases not supported for file restore")
            return False
            
    except Exception as e:
        print(f"  ❌ Error restoring SQLite database: {e}")
        return False


def restore_vector_store(backup_dir: Path) -> bool:
    """Restore ChromaDB vector store from backup."""
    print("🔢 Restoring ChromaDB vector store...")
    
    try:
        backup_chroma_path = backup_dir / "chroma_db"
        
        if not backup_chroma_path.exists():
            print(f"  ⚠️  Backup ChromaDB not found: {backup_chroma_path}")
            return False
        
        current_chroma_path = Path(settings.CHROMA_DB_PATH)
        
        # Backup current ChromaDB if it exists
        if current_chroma_path.exists():
            backup_current_name = f"chroma_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            current_chroma_path.rename(current_chroma_path.parent / backup_current_name)
            print(f"  📋 Current ChromaDB backed up as: {backup_current_name}")
        
        # Restore from backup
        shutil.copytree(backup_chroma_path, current_chroma_path, dirs_exist_ok=True)
        print(f"  ✅ ChromaDB restored: {current_chroma_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error restoring ChromaDB: {e}")
        return False


def restore_uploaded_files(backup_dir: Path) -> bool:
    """Restore uploaded files from backup."""
    print("📎 Restoring uploaded files...")
    
    try:
        backup_upload_path = backup_dir / "uploads"
        
        if not backup_upload_path.exists():
            print(f"  ⚠️  Backup uploads not found: {backup_upload_path}")
            return False
        
        current_upload_path = Path(settings.UPLOAD_DIR)
        
        # Backup current uploads if they exist
        if current_upload_path.exists():
            backup_current_name = f"uploads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            current_upload_path.rename(current_upload_path.parent / backup_current_name)
            print(f"  📋 Current uploads backed up as: {backup_current_name}")
        
        # Restore from backup
        shutil.copytree(backup_upload_path, current_upload_path, dirs_exist_ok=True)
        print(f"  ✅ Uploads restored: {current_upload_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error restoring uploads: {e}")
        return False


def verify_restore(backup_stats: dict) -> bool:
    """Verify the restored data matches the backup."""
    print("🔍 Verifying restored data...")
    
    try:
        # Check if vector store is accessible
        vector_store = VectorStore()
        current_info = vector_store.get_collection_info()
        
        expected_count = backup_stats.get("vector_store", {}).get("document_count", 0)
        actual_count = current_info.get("document_count", 0)
        
        print(f"  📊 Vector documents: {actual_count} (expected: {expected_count})")
        
        if expected_count > 0 and actual_count != expected_count:
            print(f"  ⚠️  Vector count mismatch! Expected {expected_count}, got {actual_count}")
            return False
        
        print("  ✅ Verification completed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Error during verification: {e}")
        return False


def cleanup_temp_files(backup_dir: Path):
    """Clean up temporary extraction files."""
    if "temp_" in backup_dir.name:
        try:
            shutil.rmtree(backup_dir.parent / f"temp_{backup_dir.name}")
            print("🧹 Cleaned up temporary files")
        except Exception:
            pass


def main():
    """Main restore function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Restore DocuRAG database and storage")
    parser.add_argument(
        "backup_name",
        nargs="?",
        help="Backup name to restore (will list available if not provided)"
    )
    parser.add_argument(
        "--no-files",
        action="store_true",
        help="Skip restoring uploaded files"
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only restore database (skip vector store and files)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # List available backups if no backup name provided
    if not args.backup_name:
        backups = list_available_backups()
        
        if not backups:
            print("❌ No backups found in 'backups' directory")
            return 1
        
        print("\n📋 Available backups:")
        print("-" * 60)
        for i, backup in enumerate(backups, 1):
            size_mb = backup["size"] / (1024 * 1024)
            print(f"{i:2d}. {backup['name']} ({backup['type']}, {size_mb:.1f} MB)")
        
        print("\nTo restore a backup, run:")
        print("python scripts/restore_db.py <backup_name>")
        return 0
    
    # Find the specified backup
    backups = list_available_backups()
    backup_to_restore = None
    
    for backup in backups:
        if backup["name"] == args.backup_name:
            backup_to_restore = backup
            break
    
    if not backup_to_restore:
        print(f"❌ Backup '{args.backup_name}' not found")
        return 1
    
    print("\n" + "="*60)
    print("DOCURAG DATABASE RESTORE")
    print("="*60)
    
    # Extract backup if needed
    backup_dir = extract_backup_if_needed(backup_to_restore["path"])
    
    # Load backup stats
    backup_stats = load_backup_stats(backup_dir)
    
    if backup_stats:
        print(f"📊 Backup from: {backup_stats.get('backup_timestamp', 'Unknown')}")
        print(f"📄 Documents: {backup_stats.get('total_documents', 'Unknown')}")
        print(f"🔢 Chunks: {backup_stats.get('total_chunks', 'Unknown')}")
        print(f"🗂️  Vectors: {backup_stats.get('vector_store', {}).get('document_count', 'Unknown')}")
    
    # Confirmation prompt
    if not args.force:
        print(f"\n⚠️  WARNING: This will replace your current DocuRAG data!")
        print(f"Restoring from: {backup_to_restore['name']}")
        print("Current data will be backed up before replacement.")
        
        confirm = input("\nAre you sure you want to proceed? (type 'yes' to confirm): ")
        if confirm.lower() != 'yes':
            print("Restore cancelled.")
            cleanup_temp_files(backup_dir)
            return 0
    
    success = True
    
    # Restore SQLite database
    if not restore_sqlite_database(backup_dir):
        success = False
    
    # Restore vector store (unless db-only)
    if not args.db_only:
        if not restore_vector_store(backup_dir):
            success = False
    
    # Restore uploaded files (unless no-files or db-only)
    if not args.no_files and not args.db_only:
        if not restore_uploaded_files(backup_dir):
            success = False
    
    # Verify restore
    if success and backup_stats:
        if not verify_restore(backup_stats):
            success = False
    
    # Cleanup
    cleanup_temp_files(backup_dir)
    
    print("\n" + "="*60)
    if success:
        print("✅ RESTORE COMPLETED SUCCESSFULLY!")
        print("Your DocuRAG system has been restored from backup.")
        print("You can now start the server and use the system.")
    else:
        print("❌ RESTORE COMPLETED WITH ERRORS!")
        print("Please check the error messages above.")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 