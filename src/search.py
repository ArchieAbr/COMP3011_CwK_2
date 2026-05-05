import sqlite3
import math
import json
from src.indexer import normalise_text

def get_total_documents(conn):
    """Retrieves the global document count for IDF calculations."""
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'total_documents'")
    result = cursor.fetchone()
    return result[0] if result else 0

def get_word_index(conn, word):
    """
    Retrieves the inverted index statistics for a single word.
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
    Executes a multi-word search query using TF-IDF ranking.
    Supports Exact Phrase Matching if the query is wrapped in double quotes.
    """
    # Detect exact phrase mode ("query") before normalisation strips the quotes
    is_exact_phrase = query_string.strip().startswith('"') and query_string.strip().endswith('"')
    
    words = normalise_text(query_string)
    if not words:
        return []

    unique_words = list(set(words))
    num_unique_words = len(unique_words)
    total_docs = get_total_documents(conn)
    
    if total_docs == 0:
        return []

    cursor = conn.cursor()
    
    # Pre-calculate Document Frequency (DF) for each unique word
    df_dict = {}
    for word in unique_words:
        cursor.execute("SELECT COUNT(url) FROM inverted_index WHERE word = ?", (word,))
        df_dict[word] = cursor.fetchone()[0]

    # Fetch all candidate rows matching our search terms
    placeholders = ', '.join(['?'] * num_unique_words)
    cursor.execute(f'''
        SELECT url, word, frequency, positions
        FROM inverted_index
        WHERE word IN ({placeholders})
    ''', unique_words)
    
    # Structure the data by URL for Python processing
    url_data = {}
    for url, word, freq, positions_json in cursor.fetchall():
        if url not in url_data:
            url_data[url] = {}
        url_data[url][word] = {
            "frequency": freq,
            "positions": json.loads(positions_json)
        }
    
    results = []
    
    for url, word_info in url_data.items():
        # Boolean AND Check: The URL must contain all unique search terms
        if len(word_info) != num_unique_words:
            continue
            
        # Exact Phrase Verification
        if is_exact_phrase and len(words) > 1:
            valid_phrase = False
            first_word = words[0]
            first_word_positions = word_info[first_word]["positions"]
            
            # Check if subsequent words immediately follow the first word's positions
            for start_pos in first_word_positions:
                is_match = True
                for i in range(1, len(words)):
                    next_word = words[i]
                    if (start_pos + i) not in word_info[next_word]["positions"]:
                        is_match = False
                        break
                if is_match:
                    valid_phrase = True
                    break
                    
            if not valid_phrase:
                continue 
        
        # Calculate TF-IDF Score
        score = 0.0
        for word in unique_words:
            tf = word_info[word]["frequency"]
            df = df_dict[word]
            
            # IDF = log10(Total Documents / Documents containing the word)
            idf = math.log10(total_docs / df) if df > 0 else 0
            score += (tf * idf)
            
        # Format the score to 4 decimal places for clean display
        results.append((url, round(score, 4)))
        
    # Sort results by the calculated TF-IDF score in descending order
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results

# --- Quick Test Block ---
if __name__ == '__main__':
    from src.indexer import get_db_connection, initialise_database, index_page
    import os
    
    # Clean up old test DB if it exists
    if os.path.exists("data/test_index.sqlite"):
        os.remove("data/test_index.sqlite")
        
    conn = get_db_connection("test_index.sqlite")
    initialise_database(conn)
    
    # Document 1 has the word "the" many times, Document 2 has "fox"
    index_page(conn, "http://page1.com", "The the the the the dog.")
    index_page(conn, "http://page2.com", "The quick brown fox.")
    index_page(conn, "http://page3.com", "A brown fox is fast.")
    
    print("TF-IDF Test ('the fox'):")
    # 'page2.com' should win because 'fox' is rare (high IDF), 
    # outweighing page1's spamming of the common word 'the' (low IDF)
    print(search_query(conn, "the fox"))
    
    print("\nExact Phrase Test ('\"brown fox\"'):")
    print(search_query(conn, '"brown fox"'))
    
    conn.close()