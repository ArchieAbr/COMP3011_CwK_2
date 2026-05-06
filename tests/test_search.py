import pytest
from src.search import search_query, get_word_index, get_total_documents

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


def test_get_word_index_returns_empty_for_unknown_word(populated_db):
    """Tests that get_word_index returns an empty list for a word not in the index."""
    results = get_word_index(populated_db, "zzznomatch")
    assert results == []


def test_search_returns_empty_when_no_documents(empty_db):
    """Tests that search_query returns an empty list when the index contains no documents."""
    results = search_query(empty_db, "fox")
    assert results == []


def test_search_tfidf_orders_multiple_results(populated_db):
    """
    Tests that results with multiple matches are sorted in descending score order.
    'brown fox' appears in page2 and page3. page3 does not have 'the' reducing its
    IDF penalty, so both should be returned and page2 should rank first due to 'the'
    contributing a positive (if small) score on top.
    """
    results = search_query(populated_db, "brown fox")
    assert len(results) == 2
    # Scores must be in descending order
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_single_word_exact_phrase(populated_db):
    """Tests that a single word wrapped in quotes behaves like a normal single-word search."""
    quoted_results = search_query(populated_db, '"fox"')
    plain_results = search_query(populated_db, 'fox')
    # Both should return the same set of URLs
    assert {url for url, _ in quoted_results} == {url for url, _ in plain_results}