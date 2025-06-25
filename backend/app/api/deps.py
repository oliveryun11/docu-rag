"""
API dependencies and common utilities.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings


def get_database() -> Generator[Session, None, None]:
    """
    Database dependency.
    
    Yields:
        Session: SQLAlchemy database session
    """
    yield from get_db()


def get_settings():
    """
    Settings dependency.
    
    Returns:
        Settings: Application settings
    """
    return settings 