"""
Agno-native memory and storage configuration for IntelliExtract.
Uses Agno's Memory v2 SqliteMemoryDb for persistent agent memory.
"""
import os
from pathlib import Path
from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.storage.sqlite import SqliteStorage
from typing import Optional


def get_memory(db_file: str = "intelliextract.db", table_name: str = "agent_memories") -> Memory:
    """
    Shared memory for all agents using Agno Memory v2.
    
    Args:
        db_file: SQLite database file path
        table_name: Table name for storing memories
        
    Returns:
        Memory instance with SqliteMemoryDb backend
    """
    # Ensure database directory exists
    db_path = Path(db_file)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    memory_db = SqliteMemoryDb(
        table_name=table_name,
        db_file=str(db_path)
    )
    
    return Memory(db=memory_db)


def get_storage(db_file: str = "intelliextract.db", table_name: str = "agent_sessions") -> SqliteStorage:
    """
    Shared storage for agent sessions using Agno SqliteStorage.
    
    Args:
        db_file: SQLite database file path  
        table_name: Table name for storing sessions
        
    Returns:
        SqliteStorage instance for session persistence
    """
    # Ensure database directory exists
    db_path = Path(db_file)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return SqliteStorage(
        table_name=table_name,
        db_file=str(db_path),
        auto_upgrade_schema=True
    )


def get_user_memory(user_id: str, db_file: str = "intelliextract.db") -> Memory:
    """
    Get user-specific memory for personalized agent interactions.
    
    Args:
        user_id: Unique user identifier
        db_file: SQLite database file path
        
    Returns:
        Memory instance configured for user-specific storage
    """
    memory = get_memory(db_file=db_file, table_name=f"user_memories_{user_id}")
    return memory


def get_session_memory(session_id: str, db_file: str = "intelliextract.db") -> Memory:
    """
    Get session-specific memory for request isolation.
    
    Args:
        session_id: Unique session identifier  
        db_file: SQLite database file path
        
    Returns:
        Memory instance configured for session-specific storage
    """
    memory = get_memory(db_file=db_file, table_name=f"session_memories_{session_id}")
    return memory