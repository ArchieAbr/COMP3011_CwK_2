import pytest
import sqlite3
from src.indexer import initialise_database, index_page

@pytest.fixture
def empty_db():
    """Provides an empty, in-memory SQLite database with the correct schema."""
    # Using ':memory:' creates a temporary database entirely in RAM
    conn = sqlite3.connect(":memory:")
    initialise_database(conn)
    yield conn
    conn.close()

@pytest.fixture
def populated_db(empty_db):
    """Provides an in-memory database pre-populated with test documents."""
    # Document 1: Spams the word 'the', contains 'dog'
    index_page(empty_db, "http://page1.com", "The the the the the dog.")
    # Document 2: Contains 'the', 'quick', 'brown', 'fox'
    index_page(empty_db, "http://page2.com", "The quick brown fox.")
    # Document 3: Contains 'brown', 'fox', 'fast'
    index_page(empty_db, "http://page3.com", "A brown fox is fast.")
    
    return empty_db