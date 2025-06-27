#!/usr/bin/env python3
"""
Bulk document indexing script for Kant's philosophical works.
Processes all text files in the docs_data/kant directory.

This script is optimized for philosophical text documents with YAML frontmatter.

Features:
- Simple, fast processing of all files found
- Batch processing for better performance  
- Automatic title extraction from YAML frontmatter
- No duplicate detection (handled at API level)

Note: Duplicate detection should be implemented in the API layer for better control.
"""

import sys
import os
import time
import yaml
from pathlib import Path
from typing import List, Dict, Any
from io import BytesIO

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import UploadFile
from sqlalchemy.orm import sessionmaker
from app.config.database import get_db
from app.services.document_processor import DocumentService
from app.services.indexing_service import IndexingService
from app.models.enums import FileType, DocumentStatus
from app.models.database import Document


class MockUploadFile:
    """Mock UploadFile for bulk processing existing files."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.content_type = "text/plain"
        self._content = None
    
    async def read(self) -> bytes:
        """Read file content."""
        if self._content is None:
            with open(self.file_path, 'rb') as f:
                self._content = f.read()
        return self._content
    
    async def seek(self, offset: int):
        """Seek to position (not used in our case)."""
        pass


class KantBulkIndexer:
    """Bulk document indexing utility for Kant's works."""
    
    def __init__(self):
        """Initialize the bulk indexer."""
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
    
    def find_text_files(self, directory: str) -> List[Path]:
        """
        Find all text files in the given directory recursively.
        
        Args:
            directory: Directory to search
            
        Returns:
            List[Path]: List of text file paths
        """
        docs_path = Path(directory)
        if not docs_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        text_files = list(docs_path.rglob("*.txt"))
        print(f"Found {len(text_files)} text files in {directory}")
        return text_files
    
    def _extract_frontmatter_title(self, file_path: Path) -> str:
        """
        Extract title from YAML frontmatter in the file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Title from frontmatter or generated from filename
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file starts with YAML frontmatter
            if content.startswith('---\n'):
                # Find the end of frontmatter
                end_marker = content.find('\n---\n', 4)
                if end_marker != -1:
                    frontmatter_text = content[4:end_marker]
                    try:
                        frontmatter = yaml.safe_load(frontmatter_text)
                        if frontmatter and 'title' in frontmatter:
                            return frontmatter['title']
                    except yaml.YAMLError:
                        pass
        except Exception:
            pass
        
        # Fallback to filename-based title generation
        return self._generate_title_from_filename(file_path)
    
    def _generate_title_from_filename(self, file_path: Path) -> str:
        """
        Generate a readable title from the filename.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Generated title
        """
        filename = file_path.stem
        
        # Remove number prefixes like "01-", "02-"
        if '-' in filename and filename.split('-')[0].isdigit():
            filename = '-'.join(filename.split('-')[1:])
        
        # Convert to readable format
        return filename.replace('-', ' ').title()
    
    async def upload_document(self, file_path: Path, document_service: DocumentService) -> Document:
        """
        Upload a document using the proper upload flow.
        
        Args:
            file_path: Path to the file to upload
            document_service: Document service instance
            
        Returns:
            Document: Created document
        """
        # Create mock UploadFile
        mock_file = MockUploadFile(file_path)
        
        # Use the proper upload mechanism
        document = await document_service.create_document(mock_file)
        
        # Update title and description to be more meaningful
        try:
            title = self._extract_frontmatter_title(file_path)
            document.title = title
            document.description = f"Kant's philosophical work: {title}"
            
            # Commit the title/description updates
            document_service.db.commit()
            document_service.db.refresh(document)
            
        except Exception as e:
            print(f"    Warning: Could not update title for {file_path.name}: {e}")
        
        return document
    
    async def bulk_index(self, directory: str, batch_size: int = 5) -> None:
        """
        Bulk index all text files in the directory.
        
        Args:
            directory: Directory containing text files
            batch_size: Number of files to process in each batch
        """
        self.stats['start_time'] = time.time()
        
        try:
            # Find all text files
            text_files = self.find_text_files(directory)
            self.stats['total_files'] = len(text_files)
            
            if not text_files:
                print("No text files found to process.")
                return
            
            print(f"Starting bulk indexing of {len(text_files)} Kant works...")
            print(f"Processing in batches of {batch_size}")
            
            # Process files in batches
            for i in range(0, len(text_files), batch_size):
                batch = text_files[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(text_files) + batch_size - 1) // batch_size
                
                print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} files)...")
                await self._process_batch(batch)
                
                # Small delay between batches to avoid overwhelming the system
                if i + batch_size < len(text_files):
                    time.sleep(1)
            
        except Exception as e:
            print(f"Error during bulk indexing: {e}")
            raise
        finally:
            self.stats['end_time'] = time.time()
            self._print_summary()
    
    async def _process_batch(self, files: List[Path]) -> None:
        """
        Process a batch of files.
        
        Args:
            files: List of file paths to process
        """
        db = next(get_db())
        document_service = DocumentService(db)
        indexing_service = IndexingService(db)
        
        try:
            for file_path in files:
                try:
                    print(f"  Processing: {file_path.name}")
                    
                    # Step 1: Upload document (proper upload flow)
                    document = await self.upload_document(file_path, document_service)
                    print(f"    📁 Uploaded: {document.title}")
                    
                    # Step 2: Process the document (extract, embed, index)
                    success = indexing_service.process_document(document.id)
                    
                    if success:
                        print(f"    ✅ Successfully processed: {document.title}")
                        self.stats['processed'] += 1
                    else:
                        print(f"    ❌ Failed to process: {document.title}")
                        self.stats['failed'] += 1
                        
                except Exception as e:
                    print(f"    ❌ Error processing {file_path.name}: {e}")
                    self.stats['failed'] += 1
                    
        except Exception as e:
            print(f"Error in batch processing: {e}")
            raise
        finally:
            db.close()
    
    def _print_summary(self) -> None:
        """Print indexing summary statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        print("\n" + "="*60)
        print("KANT WORKS BULK INDEXING SUMMARY")
        print("="*60)
        print(f"Total files found:     {self.stats['total_files']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed:                {self.stats['failed']}")
        print(f"Total duration:        {duration:.2f} seconds")
        
        if self.stats['total_files'] > 0:
            avg_time = duration / self.stats['total_files']
            print(f"Average time per file: {avg_time:.2f} seconds")
        
        if self.stats['total_files'] > 0:
            success_rate = (self.stats['processed'] / self.stats['total_files']) * 100
            print(f"Success rate:          {success_rate:.1f}%")
        
        print("="*60)
        print("\nKant's works are now available for RAG queries!")
        print("You can now ask questions about Kantian philosophy.")


async def main():
    """Main function to run bulk indexing for Kant's works."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bulk index Kant's philosophical works")
    parser.add_argument(
        "--directory", 
        default="docs_data/kant",
        help="Directory containing Kant's text files (default: docs_data/kant)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of files to process in each batch (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Validate directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        print("Please run 'python scripts/download_kant_works.py' first to download the works.")
        sys.exit(1)
    
    # Initialize and run bulk indexer
    try:
        indexer = KantBulkIndexer()
        
        print("🧠 Starting to index Kant's philosophical works...")
        print("📚 This will make his writings searchable in your RAG system")
        
        await indexer.bulk_index(args.directory, args.batch_size)
        
    except KeyboardInterrupt:
        print("\nIndexing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 