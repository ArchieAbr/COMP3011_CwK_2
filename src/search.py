import sqlite3
from src.indexer import normalise_text

def get_word_index(conn, word):
    """
    Retrieves the inverted index statistics for a single word.
    Returns a list of tuples containing (url, frequency, positions).
    """
    normalised_word = normalise_text(word)
    if not normalised_word:
        return []
        
    target_word = normalised_word[0]
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT url, frequency, positions 
        FROM inverted_index 
        WHERE word = ?
        ORDER BY frequency DESC
    ''', (target_word,))
    
    return cursor.fetchall()

def search_query(conn, query_string):
    """
    Executes a multi-word search query using the inverted index.
    Implements Boolean AND logic to ensure all search terms are present.
    Returns a list of URLs ranked by cumulative term frequency.
    """
    words = normalise_text(query_string)
    
    if not words:
        return []

    unique_words = list(set(words))
    cursor = conn.cursor()
    
    # Dynamically generate SQL placeholders based on the number of search terms
    placeholders = ', '.join(['?'] * len(unique_words))
    
    # SQL query groups by URL, filters for presence of all words, and ranks results
    sql = f'''
        SELECT url 
        FROM inverted_index 
        WHERE word IN ({placeholders}) 
        GROUP BY url 
        HAVING COUNT(DISTINCT word) = ? 
        ORDER BY SUM(frequency) DESC
    '''
    
    # Parameters include the target words and the required count of distinct words
    params = unique_words + [len(unique_words)]
    
    cursor.execute(sql, params)
    
    # Extract URLs from the returned tuples
    results = [row[0] for row in cursor.fetchall()]
    return results

# --- Quick Test Block ---
if __name__ == '__main__':
    from src.indexer import get_db_connection, initialise_database, index_page
    
    # Setup temporary test data
    conn = get_db_connection("test_index.sqlite")
    initialise_database(conn)
    index_page(conn, "http://page1.com", "The quick brown fox jumps.")
    index_page(conn, "http://page2.com", "The brown fox is brown.")
    index_page(conn, "http://page3.com", "A fast fox.")
    
    print("Testing 'print brown':")
    print(get_word_index(conn, "brown"))
    
    print("\nTesting 'find brown fox':")
    print(search_query(conn, "brown fox"))
    
    conn.close()