import pytest
import json
from src.indexer import normalise_text, index_page

def test_normalise_text_removes_punctuation():
    """Verifies that punctuation is stripped and text is converted to lowercase."""
    text = "Hello, World! This is a TEST."
    expected = ["hello", "world", "this", "is", "a", "test"]
    assert normalise_text(text) == expected

def test_index_page_inserts_data(empty_db):
    """Verifies that text is correctly processed and inserted into the database."""
    url = "http://test.com"
    text = "apple banana apple"
    
    index_page(empty_db, url, text)
    
    cursor = empty_db.cursor()
    cursor.execute("SELECT word, frequency, positions FROM inverted_index ORDER BY word")
    results = cursor.fetchall()
    
    assert len(results) == 2
    
    # Verify 'apple' statistics
    assert results[0][0] == "apple"
    assert results[0][1] == 2
    assert json.loads(results[0][2]) == [0, 2]
    
    # Verify 'banana' statistics
    assert results[1][0] == "banana"
    assert results[1][1] == 1
    assert json.loads(results[1][2]) == [1]

def test_index_page_updates_metadata(empty_db):
    """Verifies that the global document counter increments correctly."""
    index_page(empty_db, "http://test1.com", "test")
    index_page(empty_db, "http://test2.com", "test")
    
    cursor = empty_db.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'total_documents'")
    result = cursor.fetchone()
    
    assert result[0] == 2