#!/usr/bin/env python3
"""
List and manage DocuRAG database backups.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"


def format_time(timestamp: float) -> str:
    """Format timestamp in human-readable format."""
    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago ({dt.strftime('%Y-%m-%d %H:%M')})"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago ({dt.strftime('%H:%M')})"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago ({dt.strftime('%H:%M')})"
    else:
        return f"just now ({dt.strftime('%H:%M')})"


def load_backup_stats(backup_path: Path) -> dict:
    """Load backup statistics if available."""
    if backup_path.is_dir():
        stats_file = backup_path / "backup_stats.json"
    else:
        # For zip files, we can't easily read the stats without extracting
        return {}
    
    if stats_file.exists():
        try:
            with open(stats_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    return {}


def list_backups(detailed: bool = False):
    """List all available backups."""
    backup_base = Path("backups")
    
    if not backup_base.exists():
        print("❌ No backups directory found")
        return []
    
    backups = []
    
    # Look for both directories and zip files
    for item in backup_base.iterdir():
        if item.is_dir():
            size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            backup_type = "directory"
        elif item.suffix == ".zip":
            size = item.stat().st_size
            backup_type = "archive"
        else:
            continue
        
        backup_info = {
            "name": item.stem if item.suffix == ".zip" else item.name,
            "path": item,
            "type": backup_type,
            "size": size,
            "modified": item.stat().st_mtime,
            "stats": load_backup_stats(item) if backup_type == "directory" else {}
        }
        
        backups.append(backup_info)
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x["modified"], reverse=True)
    
    if not backups:
        print("📁 No backups found")
        return backups
    
    print(f"\n📋 Found {len(backups)} backup(s):")
    print("=" * 80)
    
    for i, backup in enumerate(backups, 1):
        stats = backup["stats"]
        
        print(f"{i:2d}. {backup['name']}")
        print(f"    Type: {backup['type']} | Size: {format_size(backup['size'])}")
        print(f"    Created: {format_time(backup['modified'])}")
        
        if detailed and stats:
            print(f"    📊 Statistics:")
            print(f"       • {stats.get('total_documents', '?')} documents")
            print(f"       • {stats.get('total_chunks', '?')} chunks")
            print(f"       • {stats.get('vector_store', {}).get('document_count', '?')} vectors")
            
            if 'documents_by_status' in stats:
                status_summary = ", ".join([f"{k}:{v}" for k, v in stats['documents_by_status'].items()])
                print(f"       • Status: {status_summary}")
        
        print()
    
    return backups


def delete_backup(backup_name: str, force: bool = False):
    """Delete a specific backup."""
    backup_base = Path("backups")
    backup_found = False
    
    # Look for both directory and zip file
    for suffix in ["", ".zip"]:
        backup_path = backup_base / f"{backup_name}{suffix}"
        if backup_path.exists():
            backup_found = True
            
            if not force:
                print(f"⚠️  Are you sure you want to delete backup '{backup_name}'?")
                confirm = input("Type 'yes' to confirm: ")
                if confirm.lower() != 'yes':
                    print("Deletion cancelled.")
                    return False
            
            try:
                if backup_path.is_dir():
                    import shutil
                    shutil.rmtree(backup_path)
                else:
                    backup_path.unlink()
                
                print(f"✅ Deleted backup: {backup_name}")
                return True
                
            except Exception as e:
                print(f"❌ Error deleting backup: {e}")
                return False
    
    if not backup_found:
        print(f"❌ Backup '{backup_name}' not found")
        return False


def cleanup_old_backups(keep_count: int = 5, keep_days: int = 30):
    """Clean up old backups based on count and age."""
    backup_base = Path("backups")
    
    if not backup_base.exists():
        print("❌ No backups directory found")
        return
    
    backups = []
    current_time = datetime.now().timestamp()
    
    # Collect all backups
    for item in backup_base.iterdir():
        if item.is_dir() or item.suffix == ".zip":
            backups.append({
                "path": item,
                "name": item.stem if item.suffix == ".zip" else item.name,
                "modified": item.stat().st_mtime,
                "age_days": (current_time - item.stat().st_mtime) / (24 * 3600)
            })
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x["modified"], reverse=True)
    
    deleted_count = 0
    
    # Delete backups beyond keep_count
    if len(backups) > keep_count:
        print(f"🧹 Keeping {keep_count} most recent backups...")
        for backup in backups[keep_count:]:
            try:
                if backup["path"].is_dir():
                    import shutil
                    shutil.rmtree(backup["path"])
                else:
                    backup["path"].unlink()
                
                print(f"  ✅ Deleted old backup: {backup['name']}")
                deleted_count += 1
                
            except Exception as e:
                print(f"  ❌ Error deleting {backup['name']}: {e}")
    
    # Delete backups older than keep_days
    old_backups = [b for b in backups[:keep_count] if b["age_days"] > keep_days]
    if old_backups:
        print(f"🧹 Deleting backups older than {keep_days} days...")
        for backup in old_backups:
            try:
                if backup["path"].is_dir():
                    import shutil
                    shutil.rmtree(backup["path"])
                else:
                    backup["path"].unlink()
                
                print(f"  ✅ Deleted old backup: {backup['name']} ({backup['age_days']:.1f} days old)")
                deleted_count += 1
                
            except Exception as e:
                print(f"  ❌ Error deleting {backup['name']}: {e}")
    
    if deleted_count == 0:
        print("✅ No backups needed to be cleaned up")
    else:
        print(f"✅ Cleaned up {deleted_count} old backup(s)")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="List and manage DocuRAG backups")
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed backup information"
    )
    parser.add_argument(
        "--delete",
        type=str,
        help="Delete a specific backup by name"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up old backups"
    )
    parser.add_argument(
        "--keep-count",
        type=int,
        default=5,
        help="Number of recent backups to keep (default: 5)"
    )
    parser.add_argument(
        "--keep-days",
        type=int,
        default=30,
        help="Maximum age in days for backups (default: 30)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    args = parser.parse_args()
    
    if args.delete:
        return 0 if delete_backup(args.delete, args.force) else 1
    elif args.cleanup:
        cleanup_old_backups(args.keep_count, args.keep_days)
        return 0
    else:
        list_backups(args.detailed)
        return 0


if __name__ == "__main__":
    sys.exit(main()) 