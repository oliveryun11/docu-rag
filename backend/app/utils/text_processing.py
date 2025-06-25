"""
Text processing utilities using LangChain for document loading and chunking.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from langchain_community.document_loaders import (
    TextLoader, 
    UnstructuredMarkdownLoader,
    PyPDFLoader,
    Docx2txtLoader
)
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter
)
from langchain.schema import Document as LangChainDocument

from app.models.enums import FileType
from app.config.settings import settings


class DocumentLoader:
    """Document loader that handles different file types using LangChain."""
    
    @staticmethod
    def get_loader(file_path: str, file_type: FileType):
        """
        Get appropriate LangChain loader for file type.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            
        Returns:
            LangChain document loader
            
        Raises:
            ValueError: If file type is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_type == FileType.TXT:
            return TextLoader(file_path, encoding='utf-8')
        elif file_type == FileType.MARKDOWN:
            # Check if it's an MDX file by extension
            if file_path.lower().endswith('.mdx'):
                # For MDX files, use TextLoader to preserve JSX and components
                return TextLoader(file_path, encoding='utf-8')
            else:
                # For regular markdown files, try UnstructuredMarkdownLoader
                try:
                    return UnstructuredMarkdownLoader(file_path)
                except ImportError:
                    # Fallback to TextLoader if unstructured is not available
                    return TextLoader(file_path, encoding='utf-8')
        elif file_type == FileType.PDF:
            return PyPDFLoader(file_path)
        elif file_type == FileType.DOCX:
            return Docx2txtLoader(file_path)
        elif file_type == FileType.HTML:
            # For HTML, we'll use text loader as fallback
            return TextLoader(file_path, encoding='utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    @staticmethod
    def load_document(file_path: str, file_type: FileType) -> List[LangChainDocument]:
        """
        Load document content using appropriate loader.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            
        Returns:
            List[LangChainDocument]: Loaded document pages/sections
            
        Raises:
            Exception: If loading fails
        """
        try:
            loader = DocumentLoader.get_loader(file_path, file_type)
            documents = loader.load()
            
            # Add file metadata to each document
            for doc in documents:
                doc.metadata.update({
                    'source_file': file_path,
                    'file_type': file_type.value,
                    'file_name': os.path.basename(file_path)
                })
            
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to load document {file_path}: {str(e)}")


class TextChunker:
    """Text chunker using LangChain's intelligent text splitters."""
    
    def __init__(self):
        self.chunk_size = settings.MAX_CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    def get_markdown_splitter(self) -> MarkdownHeaderTextSplitter:
        """
        Get markdown-aware text splitter that preserves headers.
        
        Returns:
            MarkdownHeaderTextSplitter: Configured markdown splitter
        """
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"), 
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        
        return MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
    
    def get_recursive_splitter(self) -> RecursiveCharacterTextSplitter:
        """
        Get recursive character text splitter for general use.
        
        Returns:
            RecursiveCharacterTextSplitter: Configured recursive splitter
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_documents(
        self, 
        documents: List[LangChainDocument], 
        file_type: FileType
    ) -> List[LangChainDocument]:
        """
        Chunk documents using appropriate splitter based on file type.
        
        Args:
            documents: List of LangChain documents
            file_type: Type of source file
            
        Returns:
            List[LangChainDocument]: Chunked documents
        """
        if file_type == FileType.MARKDOWN:
            return self._chunk_markdown(documents)
        else:
            return self._chunk_recursive(documents)
    
    def _chunk_markdown(self, documents: List[LangChainDocument]) -> List[LangChainDocument]:
        """
        Chunk markdown documents preserving header structure.
        
        Args:
            documents: Markdown documents
            
        Returns:
            List[LangChainDocument]: Chunked documents
        """
        all_chunks = []
        
        for doc in documents:
            # First split by markdown headers
            md_splitter = self.get_markdown_splitter()
            header_chunks = md_splitter.split_text(doc.page_content)
            
            # Then apply recursive splitting to large chunks
            recursive_splitter = self.get_recursive_splitter()
            
            for chunk in header_chunks:
                # If chunk is too large, split it further
                if len(chunk.page_content) > self.chunk_size:
                    sub_chunks = recursive_splitter.split_documents([chunk])
                    all_chunks.extend(sub_chunks)
                else:
                    all_chunks.append(chunk)
        
        return all_chunks
    
    def _chunk_recursive(self, documents: List[LangChainDocument]) -> List[LangChainDocument]:
        """
        Chunk documents using recursive character splitter.
        
        Args:
            documents: Documents to chunk
            
        Returns:
            List[LangChainDocument]: Chunked documents
        """
        splitter = self.get_recursive_splitter()
        return splitter.split_documents(documents)


class DocumentProcessor:
    """Main document processor that orchestrates loading and chunking."""
    
    def __init__(self):
        self.loader = DocumentLoader()
        self.chunker = TextChunker()
    
    def process_document(
        self, 
        file_path: str, 
        file_type: FileType
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Process document: load, extract text, and chunk.
        
        Args:
            file_path: Path to the document file
            file_type: Type of the file
            
        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: (chunks, metadata)
                - chunks: List of text chunks with metadata
                - metadata: Document-level metadata (word count, etc.)
                
        Raises:
            Exception: If processing fails
        """
        try:
            # Load document
            documents = self.loader.load_document(file_path, file_type)
            
            # Combine all pages/sections into single text for metadata
            full_text = "\n\n".join([doc.page_content for doc in documents])
            
            # Skip processing if no content
            if not full_text.strip():
                return [], {'word_count': 0, 'character_count': 0, 'page_count': 0}
            
            # Calculate document metadata
            doc_metadata = self._calculate_metadata(full_text, documents)
            
            # Chunk documents
            chunks = self.chunker.chunk_documents(documents, file_type)
            
            # Limit number of chunks
            if len(chunks) > settings.MAX_CHUNKS_PER_DOCUMENT:
                chunks = chunks[:settings.MAX_CHUNKS_PER_DOCUMENT]
            
            # Convert chunks to dict format for database storage
            chunk_data = []
            for i, chunk in enumerate(chunks):
                chunk_info = {
                    'content': chunk.page_content,
                    'chunk_index': i,
                    'character_count': len(chunk.page_content),
                    'word_count': len(chunk.page_content.split()),
                    'metadata': chunk.metadata,
                    'start_page': chunk.metadata.get('page', None),
                    'end_page': chunk.metadata.get('page', None)
                }
                chunk_data.append(chunk_info)
            
            return chunk_data, doc_metadata
            
        except Exception as e:
            raise Exception(f"Failed to process document: {str(e)}")
    
    def _calculate_metadata(
        self, 
        full_text: str, 
        documents: List[LangChainDocument]
    ) -> Dict[str, Any]:
        """
        Calculate document-level metadata.
        
        Args:
            full_text: Complete document text
            documents: Original document pages
            
        Returns:
            Dict[str, Any]: Document metadata
        """
        return {
            'word_count': len(full_text.split()),
            'character_count': len(full_text),
            'page_count': len(documents) if documents else 1,
            'estimated_reading_time_minutes': max(1, len(full_text.split()) // 200)
        }


def extract_text_preview(content: str, max_length: int = 200) -> str:
    """
    Extract a preview of text content for display.
    
    Args:
        content: Full text content
        max_length: Maximum length of preview
        
    Returns:
        str: Preview text
    """
    if len(content) <= max_length:
        return content
    
    # Find a good breaking point (end of sentence or word)
    truncated = content[:max_length]
    
    # Try to break at sentence end
    last_period = truncated.rfind('.')
    if last_period > max_length * 0.7:  # If we find a period in the last 30%
        return truncated[:last_period + 1]
    
    # Otherwise break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + "..."
    
    return truncated + "..."


def count_tokens_estimate(text: str) -> int:
    """
    Estimate token count for text (rough approximation).
    
    Args:
        text: Text to count tokens for
        
    Returns:
        int: Estimated token count
    """
    # Rough approximation: 1 token ≈ 4 characters for English text
    return len(text) // 4 