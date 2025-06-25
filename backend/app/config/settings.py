"""
Application settings and configuration management.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Settings
    APP_NAME: str = Field(default="DocuRAG Backend", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=False, description="Auto-reload on code changes")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./docu_rag.db",
        description="Database connection URL"
    )
    
    # Gemini API Configuration
    GOOGLE_API_KEY: str = Field(default="", description="Google API key for Gemini")
    GEMINI_MODEL: str = Field(
        default="gemini-pro",
        description="Gemini model name"
    )
    GEMINI_EMBEDDING_MODEL: str = Field(
        default="models/embedding-001",
        description="Gemini embedding model name"
    )
    
    # ChromaDB Configuration
    CHROMA_DB_PATH: str = Field(
        default="./chroma_db",
        description="ChromaDB storage path"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="documents",
        description="ChromaDB collection name"
    )
    
    # File Storage Configuration
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Upload directory path"
    )
    MAX_FILE_SIZE_MB: int = Field(
        default=10,
        description="Maximum file size in MB"
    )
    ALLOWED_FILE_TYPES: str = Field(
        default="pdf,txt,md,mdx,docx",
        description="Allowed file extensions (comma-separated)"
    )
    
    # Security
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", description="Secret key for JWT tokens")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        description="Rate limit requests per minute"
    )
    
    # Processing Configuration
    MAX_CHUNK_SIZE: int = Field(
        default=1000,
        description="Maximum chunk size for text splitting"
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        description="Overlap between text chunks"
    )
    MAX_CHUNKS_PER_DOCUMENT: int = Field(
        default=100,
        description="Maximum chunks per document"
    )
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse comma-separated file types into a list."""
        return [ext.strip() for ext in self.ALLOWED_FILE_TYPES.split(",") if ext.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings() 