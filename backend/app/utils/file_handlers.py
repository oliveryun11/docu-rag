"""
File handling utilities for document uploads and storage.
"""

import os
import hashlib
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile
from datetime import datetime

from app.config.settings import settings
from app.models.enums import FileType


def validate_file_type(filename: str) -> FileType:
    """
    Validate file type based on extension.
    
    Args:
        filename: Original filename
        
    Returns:
        FileType: Validated file type enum
        
    Raises:
        HTTPException: If file type is not supported
    """
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # Map extensions to FileType enum
    extension_mapping = {
        'pdf': FileType.PDF,
        'txt': FileType.TXT,
        'md': FileType.MARKDOWN,
        'mdx': FileType.MARKDOWN,
        'markdown': FileType.MARKDOWN,
        'docx': FileType.DOCX,
        'html': FileType.HTML,
        'htm': FileType.HTML
    }
    
    if file_extension not in extension_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. "
                   f"Supported types: {settings.ALLOWED_FILE_TYPES}"
        )
    
    return extension_mapping[file_extension]


def validate_file_size(file_size: int) -> None:
    """
    Validate file size against maximum allowed size.
    
    Args:
        file_size: File size in bytes
        
    Raises:
        HTTPException: If file is too large
    """
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB, "
                   f"received: {file_size / (1024 * 1024):.1f}MB"
        )


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename to prevent conflicts.
    
    Args:
        original_filename: Original uploaded filename
        
    Returns:
        str: Unique filename with timestamp and UUID
    """
    # Extract file extension
    file_extension = ''
    if '.' in original_filename:
        file_extension = '.' + original_filename.split('.')[-1].lower()
    
    # Generate unique name: timestamp_uuid_original
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    base_name = original_filename.replace(file_extension, '') if file_extension else original_filename
    
    # Clean base name (remove special characters)
    clean_base = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_base = clean_base.replace(' ', '_')[:50]  # Limit length
    
    return f"{timestamp}_{unique_id}_{clean_base}{file_extension}"


def ensure_upload_directory() -> Path:
    """
    Ensure upload directory exists.
    
    Returns:
        Path: Upload directory path
    """
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_uploaded_file(file: UploadFile) -> Tuple[str, str, int]:
    """
    Save uploaded file to disk.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Tuple[str, str, int]: (unique_filename, file_path, file_size)
        
    Raises:
        HTTPException: If file operations fail
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate size and type
        validate_file_size(file_size)
        file_type = validate_file_type(file.filename)
        
        # Generate unique filename and path
        unique_filename = generate_unique_filename(file.filename)
        upload_dir = ensure_upload_directory()
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return unique_filename, str(file_path), file_size
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


def delete_file(file_path: str) -> bool:
    """
    Delete file from disk.
    
    Args:
        file_path: Path to file to delete
        
    Returns:
        bool: True if successful, False if file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def get_file_hash(file_path: str) -> Optional[str]:
    """
    Calculate MD5 hash of file for duplicate detection.
    
    Args:
        file_path: Path to file
        
    Returns:
        Optional[str]: MD5 hash or None if file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB" 