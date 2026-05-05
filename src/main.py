import cmd
import sys
from src.crawler import WebCrawler
from src.indexer import get_db_connection, initialise_database, index_page
from src.search import search_query, get_word_index

class SearchEngineShell(cmd.Cmd):
    intro = 'Welcome to the Search Engine. Type help or ? to list commands.\n'
    prompt = '> '

    def __init__(self):
        super().__init__()
        # Maintains the active database connection in memory
        self.conn = None

    def do_build(self, arg):
        """
        Instructs the search tool to crawl the website, build the index, 
        and save the resulting index into the file system.
        Usage: build
        """
        print("Executing: Crawling site and building SQLite index...")
        crawler = WebCrawler()
        
        # Setup a fresh database connection for the build process
        build_conn = get_db_connection("index.sqlite")
        initialise_database(build_conn)
        
        current_url = crawler.base_url
        pages_indexed = 0
        
        while current_url:
            html = crawler.fetch_page(current_url)
            if not html:
                print(f"Warning: Failed to fetch {current_url}. Stopping crawl.")
                break
                
            text = crawler.extract_page_text(html)
            index_page(build_conn, current_url, text)
            pages_indexed += 1
            
            # The crawler module handles the politeness delay natively during fetch_page
            current_url = crawler.extract_next_url(html, current_url)
            
        build_conn.close()
        print(f"Build complete. Successfully crawled and indexed {pages_indexed} pages.")

    def do_load(self, arg):
        """
        Loads the index from the file system.
        Usage: load
        """
        print("Executing: Loading SQLite index from data/...")
        try:
            self.conn = get_db_connection("index.sqlite")
            print("Index loaded successfully. You may now use 'print' and 'find'.")
        except Exception as e:
            print(f"Error loading database: {e}")

    def do_print(self, arg):
        """
        Prints the inverted index for a particular word.
        Usage: print <word>
        """
        if not self.conn:
            print("Error: You must run 'load' before printing.")
            return
            
        if not arg:
            print("Error: Please provide a word to print (e.g., 'print nonsense').")
            return
        
        word = arg.strip().lower()
        results = get_word_index(self.conn, word)
        
        if not results:
            print(f"The word '{word}' was not found in the index.")
            return
            
        print(f"\nInverted index for '{word}':")
        for url, frequency, positions in results:
            print(f"  - URL: {url} | Frequency: {frequency} | Positions: {positions}")
        print()

    def do_find(self, arg):
        """
        Finds a given query phrase in the inverted index and returns 
        a list of all pages that contain it, ranked by TF-IDF score.
        Supports exact phrase matching using double quotes.
        Usage: find <query> or find "<exact phrase>"
        """
        if not self.conn:
            print("Error: You must run 'load' before searching.")
            return
            
        if not arg:
            print("Error: Please provide a query (e.g., 'find good friends').")
            return
        
        # We no longer strip quotes here, as search_query needs them to detect exact phrases
        query = arg.strip()
        results = search_query(self.conn, query)
        
        if not results:
            print(f"No pages found matching: '{query}'")
            return
            
        print(f"\nSearch results for '{query}' (Ranked by TF-IDF Relevance):")
        # Unpack the tuple to display both the URL and the algorithm's score
        for rank, (url, score) in enumerate(results, 1):
            print(f"  {rank}. {url} (Score: {score})")
        print()

    def do_exit(self, arg):
        """Exits the search engine shell."""
        if self.conn:
            self.conn.close()
        print("Exiting search engine. Goodbye!")
        return True

    do_quit = do_exit

if __name__ == '__main__':
    try:
        SearchEngineShell().cmdloop()
    except KeyboardInterrupt:
        print("\nExiting search engine. Goodbye!")
        sys.exit(0)