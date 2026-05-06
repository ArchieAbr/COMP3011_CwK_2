import pytest
from src.search import search_query, get_word_index

def test_search_boolean_and_logic(populated_db):
    """Tests that queries only return URLs containing ALL search terms."""
    # 'brown' is in page2 and page3. 'dog' is in page1.
    # No single page has both words.
    results = search_query(populated_db, "brown dog")
    assert len(results) == 0

def test_search_tfidf_ranking(populated_db):
    """Tests that TF-IDF correctly penalises common words and ranks relevant pages higher."""
    # 'the' is common (page 1, page 2). 'fox' is less common (page 2, page 3).
    # Only page 2 has both. The algorithm should calculate a positive score for it.
    results = search_query(populated_db, "the fox")
    
    assert len(results) == 1
    url, score = results[0]
    assert url == "http://page2.com"
    assert score > 0.0

def test_search_exact_phrase_matching_success(populated_db):
    """Tests that exact phrase matching returns pages with correctly ordered words."""
    # Both page 2 and page 3 have the phrase "brown fox" consecutively.
    results = search_query(populated_db, '"brown fox"')
    
    assert len(results) == 2
    urls = [r[0] for r in results]
    assert "http://page2.com" in urls
    assert "http://page3.com" in urls

def test_search_exact_phrase_matching_failure(populated_db):
    """Tests that exact phrase matching rejects pages where words are out of order."""
    # "fox brown" does not exist consecutively in that order in any document.
    results = search_query(populated_db, '"fox brown"')
    assert len(results) == 0

def test_search_empty_query(populated_db):
    """Tests that an empty query gracefully returns an empty list."""
    results = search_query(populated_db, "")
    assert results == []
    
    results_spaces = search_query(populated_db, "   ")
    assert results_spaces == []