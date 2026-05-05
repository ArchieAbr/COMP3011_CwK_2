import sqlite3
import re
import json
from pathlib import Path

def get_db_connection(db_name="index.sqlite"):
    """
    Establishes a connection to the SQLite database in the data/ directory.
    """
    # Ensure it saves in the correct directory relative to this file
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "data" / db_name
    return sqlite3.connect(db_path)

def initialise_database(conn):
    """
    Creates the inverted index schema and a metadata table for global statistics.
    """
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inverted_index (
            word TEXT,
            url TEXT,
            frequency INTEGER,
            positions TEXT,
            PRIMARY KEY (word, url)
        )
    ''')
    
    # New metadata table to track corpus-wide statistics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    
    # Initialize the document counter to 0 if it does not already exist
    cursor.execute('''
        INSERT OR IGNORE INTO metadata (key, value) VALUES ('total_documents', 0)
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON inverted_index(word)')
    conn.commit()

def normalise_text(text):
    """
    Strips punctuation and converts text to lowercase.
    """
    # Convert to lowercase to satisfy the case-insensitivity requirement
    text = text.lower()
    # Remove anything that isn't an alphanumeric character or whitespace
    text = re.sub(r'[^\w\s]', '', text)
    return text.split()

def index_page(conn, url, raw_text):
    """
    Processes raw text, calculates frequencies and positions, 
    inserts the data, and updates the global document count.
    """
    words = normalise_text(raw_text)
    word_stats = {}

    for position, word in enumerate(words):
        if word not in word_stats:
            word_stats[word] = {"frequency": 0, "positions": []}
        
        word_stats[word]["frequency"] += 1
        word_stats[word]["positions"].append(position)

    db_rows = []
    for word, stats in word_stats.items():
        db_rows.append((
            word, 
            url, 
            stats["frequency"], 
            json.dumps(stats["positions"]) 
        ))

    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR REPLACE INTO inverted_index (word, url, frequency, positions)
        VALUES (?, ?, ?, ?)
    ''', db_rows)
    
    # Increment the global document counter for TF-IDF calculations
    cursor.execute('''
        UPDATE metadata SET value = value + 1 WHERE key = 'total_documents'
    ''')
    
    conn.commit()

# --- Quick Test Block ---
if __name__ == '__main__':
    print("Testing Indexer Module...")
    test_conn = get_db_connection("test_index.sqlite")
    initialise_database(test_conn)
    
    test_url = "http://example.com/quotes"
    test_text = "Hello world! The world is a great place. Hello again."
    
    index_page(test_conn, test_url, test_text)
    print("Data indexed successfully. Check data/ folder for test_index.sqlite.")
    test_conn.close()