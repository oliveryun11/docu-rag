#!/usr/bin/env python3
"""
Bulk document indexing script for NextJS documentation.
Processes all MDX files in the docs_data/nextjs directory.
"""

import sys
import os
import time
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
        self.content_type = "text/markdown"
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


class BulkIndexer:
    """Bulk document indexing utility."""
    
    def __init__(self):
        """Initialize the bulk indexer."""
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
    
    def find_mdx_files(self, directory: str) -> List[Path]:
        """
        Find all MDX files in the given directory recursively.
        
        Args:
            directory: Directory to search
            
        Returns:
            List[Path]: List of MDX file paths
        """
        docs_path = Path(directory)
        if not docs_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        mdx_files = list(docs_path.rglob("*.mdx"))
        print(f"Found {len(mdx_files)} MDX files in {directory}")
        return mdx_files
    
    def _generate_title_from_path(self, relative_path: Path) -> str:
        """
        Generate a readable title from the file path.
        
        Args:
            relative_path: Relative path to the file
            
        Returns:
            str: Generated title
        """
        parts = list(relative_path.parts[:-1])  # Exclude filename
        filename = relative_path.stem
        
        # Clean up numbered prefixes and convert to readable format
        cleaned_parts = []
        for part in parts:
            # Remove number prefixes like "01-", "02-"
            if '-' in part and part.split('-')[0].isdigit():
                part = '-'.join(part.split('-')[1:])
            cleaned_parts.append(part.replace('-', ' ').title())
        
        # Clean up filename
        if '-' in filename and filename.split('-')[0].isdigit():
            filename = '-'.join(filename.split('-')[1:])
        filename = filename.replace('-', ' ').title()
        
        # Combine parts
        if cleaned_parts:
            return f"{' / '.join(cleaned_parts)} / {filename}"
        else:
            return filename
    
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
            relative_path = file_path.relative_to(Path("docs_data/nextjs"))
            title = self._generate_title_from_path(relative_path)
            document.title = title
            document.description = f"NextJS documentation: {title}"
            
            # Commit the title/description updates
            document_service.db.commit()
            document_service.db.refresh(document)
            
        except ValueError:
            # Fallback if relative path doesn't work
            pass
        
        return document
    
    async def bulk_index(self, directory: str, batch_size: int = 10) -> None:
        """
        Bulk index all MDX files in the directory.
        
        Args:
            directory: Directory containing MDX files
            batch_size: Number of files to process in each batch
        """
        self.stats['start_time'] = time.time()
        
        try:
            # Find all MDX files
            mdx_files = self.find_mdx_files(directory)
            self.stats['total_files'] = len(mdx_files)
            
            if not mdx_files:
                print("No MDX files found to process.")
                return
            
            print(f"Starting bulk indexing of {len(mdx_files)} files...")
            print(f"Processing in batches of {batch_size}")
            
            # Process files in batches
            for i in range(0, len(mdx_files), batch_size):
                batch = mdx_files[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(mdx_files) + batch_size - 1) // batch_size
                
                print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} files)...")
                await self._process_batch(batch)
                
                # Small delay between batches to avoid overwhelming the system
                if i + batch_size < len(mdx_files):
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
                    
                    # Check if document already exists (by file path)
                    existing_doc = db.query(Document).filter(
                        Document.file_path.like(f"%{file_path.name}")
                    ).first()
                    
                    if existing_doc:
                        print(f"    Skipped: Document already exists (ID: {existing_doc.id})")
                        self.stats['skipped'] += 1
                        continue
                    
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
        print("BULK INDEXING SUMMARY")
        print("="*60)
        print(f"Total files found:     {self.stats['total_files']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed:                {self.stats['failed']}")
        print(f"Skipped (already exist): {self.stats['skipped']}")
        print(f"Total duration:        {duration:.2f} seconds")
        
        if self.stats['processed'] > 0:
            avg_time = duration / (self.stats['processed'] + self.stats['failed'])
            print(f"Average time per file: {avg_time:.2f} seconds")
        
        success_rate = (self.stats['processed'] / max(1, self.stats['total_files'] - self.stats['skipped'])) * 100
        print(f"Success rate:          {success_rate:.1f}%")
        print("="*60)


async def main():
    """Main function to run bulk indexing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bulk index NextJS documentation")
    parser.add_argument(
        "--directory", 
        default="docs_data/nextjs",
        help="Directory containing MDX files (default: docs_data/nextjs)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of files to process in each batch (default: 5)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing of existing documents"
    )
    
    args = parser.parse_args()
    
    # Validate directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        sys.exit(1)
    
    # Initialize and run bulk indexer
    try:
        indexer = BulkIndexer()
        
        if args.force:
            print("WARNING: Force mode is not yet implemented.")
            print("This will skip documents that already exist in the database.")
        
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