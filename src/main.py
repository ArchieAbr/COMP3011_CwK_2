import cmd
import sys

class SearchEngineShell(cmd.Cmd):
    intro = 'Welcome to this Search Engine. Type help or ? to list commands.\n'
    prompt = '> '

    def do_build(self, arg):
        """
        Instructs the search tool to crawl the website, build the index, 
        and save the resulting index into the file system.
        Usage: build
        """
        print("Executing: Crawling site and building SQLite index...")
        # TODO: Call crawler.py and indexer.py logic here

    def do_load(self, arg):
        """
        Loads the index from the file system.
        Usage: load
        """
        print("Executing: Loading SQLite index from data/...")
        # TODO: Establish SQLite connection here

    def do_print(self, arg):
        """
        Prints the inverted index for a particular word.
        Usage: print <word>
        """
        if not arg:
            print("Error: Please provide a word to print (e.g., 'print nonsense').")
            return
        
        # Ensure case insensitivity
        word = arg.strip().lower()
        print(f"Executing: Fetching inverted index for the word '{word}'...")
        # TODO: Call database fetch logic here

    def do_find(self, arg):
        """
        Finds a given query phrase in the inverted index and returns 
        a list of all pages that contain it.
        Usage: find <query>
        """
        if not arg:
            print("Error: Please provide a query (e.g., 'find example query').")
            return
        
        query = arg.strip().lower()
        print(f"Executing: Searching for '{query}'...")
        # TODO: Call search.py logic here

    def do_exit(self, arg):
        """Exits the search engine shell."""
        print("Exiting search engine. Goodbye!")
        return True

    # Allow 'quit' as an alias for 'exit'
    do_quit = do_exit

if __name__ == '__main__':
    try:
        SearchEngineShell().cmdloop()
    except KeyboardInterrupt:
        print("\nExiting search engine. Goodbye!")
        sys.exit(0)