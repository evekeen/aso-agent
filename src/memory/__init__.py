"""Memory management for ASO Agent Service."""

from contextlib import AbstractAsyncContextManager

from .sqlite import get_sqlite_saver, get_sqlite_store
from src.service.settings import settings, DatabaseType


def initialize_database() -> AbstractAsyncContextManager:
    """
    Initialize the appropriate database checkpointer based on configuration.
    Returns an initialized AsyncCheckpointer instance.
    """
    if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
        # TODO: Implement PostgreSQL support
        raise NotImplementedError("PostgreSQL support not yet implemented")
    elif settings.DATABASE_TYPE == DatabaseType.MONGO:
        # TODO: Implement MongoDB support
        raise NotImplementedError("MongoDB support not yet implemented")
    else:  # Default to SQLite
        return get_sqlite_saver()


def initialize_store():
    """
    Initialize the appropriate store based on configuration.
    Returns an async context manager for the initialized store.
    """
    if settings.DATABASE_TYPE == DatabaseType.POSTGRES:
        # TODO: Implement PostgreSQL store
        raise NotImplementedError("PostgreSQL store not yet implemented")
    else:  # Default to SQLite
        return get_sqlite_store()