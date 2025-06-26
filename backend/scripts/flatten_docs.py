#!/usr/bin/env python3
"""
Script to flatten the NextJS documentation directory structure.

This script takes the nested directory structure and flattens it by moving all
MDX files to the root level with descriptive filenames based on their path.

Example:
  From: docs_data/nextjs/01-app/01-getting-started/01-installation.mdx
  To:   docs_data/nextjs/01-app_01-getting-started_01-installation.mdx
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple


def find_all_mdx_files(root_dir: Path) -> List[Path]:
    """
    Find all MDX files in the directory structure.
    
    Args:
        root_dir: Root directory to search
        
    Returns:
        List[Path]: List of MDX file paths
    """
    mdx_files = []
    for file_path in root_dir.rglob("*.mdx"):
        if file_path.is_file():
            mdx_files.append(file_path)
    return sorted(mdx_files)


def generate_flattened_name(file_path: Path, root_dir: Path) -> str:
    """
    Generate a flattened filename based on the directory path.
    
    Args:
        file_path: Original file path
        root_dir: Root directory (to calculate relative path)
        
    Returns:
        str: Flattened filename
    """
    try:
        # Get relative path from root
        relative_path = file_path.relative_to(root_dir)
        
        # Get all path parts except the filename
        path_parts = relative_path.parts[:-1]  # Exclude the filename
        filename = relative_path.parts[-1]     # Get the filename
        
        # If file is directly in root, keep original name
        if not path_parts:
            return filename
        
        # Join path parts with underscores and add filename
        flattened_prefix = "_".join(path_parts)
        
        # Remove .mdx extension, add prefix, then add back extension
        name_without_ext = filename.rsplit('.', 1)[0]
        flattened_name = f"{flattened_prefix}_{name_without_ext}.mdx"
        
        return flattened_name
        
    except ValueError:
        # Fallback if relative path doesn't work
        return file_path.name


def preview_changes(root_dir: Path) -> List[Tuple[Path, str]]:
    """
    Preview what changes will be made without actually moving files.
    
    Args:
        root_dir: Root directory
        
    Returns:
        List[Tuple[Path, str]]: List of (original_path, new_filename) tuples
    """
    mdx_files = find_all_mdx_files(root_dir)
    changes = []
    
    for file_path in mdx_files:
        new_name = generate_flattened_name(file_path, root_dir)
        changes.append((file_path, new_name))
    
    return changes


def check_for_conflicts(changes: List[Tuple[Path, str]]) -> List[str]:
    """
    Check for filename conflicts after flattening.
    
    Args:
        changes: List of (original_path, new_filename) tuples
        
    Returns:
        List[str]: List of conflicting filenames
    """
    seen_names = {}
    conflicts = []
    
    for original_path, new_name in changes:
        if new_name in seen_names:
            conflicts.append(f"Conflict: '{new_name}' would be used by:")
            conflicts.append(f"  - {seen_names[new_name]}")
            conflicts.append(f"  - {original_path}")
        else:
            seen_names[new_name] = original_path
    
    return conflicts


def flatten_directory(root_dir: Path, dry_run: bool = True) -> None:
    """
    Flatten the directory structure by moving all MDX files to root level.
    
    Args:
        root_dir: Root directory containing MDX files
        dry_run: If True, only preview changes without moving files
    """
    print(f"{'DRY RUN: ' if dry_run else ''}Flattening directory: {root_dir}")
    print("=" * 70)
    
    # Get all changes
    changes = preview_changes(root_dir)
    
    if not changes:
        print("No MDX files found to flatten.")
        return
    
    print(f"Found {len(changes)} MDX files to process.")
    
    # Check for conflicts
    conflicts = check_for_conflicts(changes)
    if conflicts:
        print("\n❌ FILENAME CONFLICTS DETECTED:")
        print("=" * 50)
        for conflict in conflicts:
            print(conflict)
        print("\nPlease resolve conflicts before proceeding.")
        return
    
    print("✅ No filename conflicts detected.")
    
    # Show preview of changes
    print(f"\n{'Preview of changes:' if dry_run else 'Applying changes:'}")
    print("-" * 50)
    
    moved_count = 0
    removed_dirs = set()
    
    for original_path, new_name in changes:
        new_path = root_dir / new_name
        
        # Show the change
        relative_original = original_path.relative_to(root_dir)
        print(f"  {relative_original} → {new_name}")
        
        if not dry_run:
            try:
                # Move the file
                shutil.move(str(original_path), str(new_path))
                moved_count += 1
                
                # Track directories that might become empty
                parent_dir = original_path.parent
                if parent_dir != root_dir:
                    removed_dirs.add(parent_dir)
                    
            except Exception as e:
                print(f"    ❌ Error moving file: {e}")
    
    if not dry_run:
        print(f"\n✅ Successfully moved {moved_count} files.")
        
        # Clean up empty directories
        print("\nCleaning up empty directories...")
        cleanup_empty_directories(root_dir, removed_dirs)
    else:
        print(f"\nDry run complete. {len(changes)} files would be moved.")
        print("Run with --execute to apply changes.")


def cleanup_empty_directories(root_dir: Path, dirs_to_check: set) -> None:
    """
    Remove empty directories after flattening.
    
    Args:
        root_dir: Root directory (won't be removed)
        dirs_to_check: Set of directories to check for emptiness
    """
    removed_count = 0
    
    # Sort directories by depth (deepest first) to remove from bottom up
    sorted_dirs = sorted(dirs_to_check, key=lambda p: len(p.parts), reverse=True)
    
    for dir_path in sorted_dirs:
        try:
            # Only remove if directory is empty and not the root
            if dir_path != root_dir and dir_path.exists() and not any(dir_path.iterdir()):
                print(f"  Removing empty directory: {dir_path.relative_to(root_dir)}")
                dir_path.rmdir()
                removed_count += 1
        except Exception as e:
            print(f"  ❌ Error removing directory {dir_path}: {e}")
    
    if removed_count > 0:
        print(f"✅ Removed {removed_count} empty directories.")
    else:
        print("No empty directories to remove.")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Flatten NextJS documentation directory structure"
    )
    parser.add_argument(
        "--directory",
        default="docs_data/nextjs",
        help="Directory to flatten (default: docs_data/nextjs)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually move files (default is dry run)"
    )
    
    args = parser.parse_args()
    
    # Validate directory exists
    root_dir = Path(args.directory)
    if not root_dir.exists():
        print(f"Error: Directory '{args.directory}' does not exist.")
        return 1
    
    if not root_dir.is_dir():
        print(f"Error: '{args.directory}' is not a directory.")
        return 1
    
    try:
        # Run flattening operation
        flatten_directory(root_dir, dry_run=not args.execute)
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 