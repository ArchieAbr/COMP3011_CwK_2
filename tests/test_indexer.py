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


def test_normalise_text_empty_string():
    """Verifies that normalising an empty string returns an empty list."""
    assert normalise_text("") == []


def test_normalise_text_preserves_numbers():
    """Verifies that numeric characters are retained after normalisation."""
    result = normalise_text("chapter 3 has 42 pages")
    assert "3" in result
    assert "42" in result


def test_index_page_updates_existing_word_on_reindex(empty_db):
    """
    Verifies INSERT OR REPLACE behaviour on the (word, url) primary key.
    Re-indexing the same URL with a different frequency for the same word
    must update the existing row rather than insert a duplicate.
    """
    url = "http://test.com"
    # First pass: 'apple' appears once
    index_page(empty_db, url, "apple")

    cursor = empty_db.cursor()
    cursor.execute("SELECT frequency FROM inverted_index WHERE word = ? AND url = ?", ("apple", url))
    assert cursor.fetchone()[0] == 1

    # Second pass: 'apple' now appears twice in the new text
    index_page(empty_db, url, "apple apple")

    cursor.execute("SELECT frequency FROM inverted_index WHERE word = ? AND url = ?", ("apple", url))
    assert cursor.fetchone()[0] == 2

    # There must still be only one row for this (word, url) pair — no duplicate inserted
    cursor.execute("SELECT COUNT(*) FROM inverted_index WHERE word = ? AND url = ?", ("apple", url))
    assert cursor.fetchone()[0] == 1