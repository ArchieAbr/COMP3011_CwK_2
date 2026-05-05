import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin

class WebCrawler:
    def __init__(self, base_url="https://quotes.toscrape.com/"):
        self.base_url = base_url
        # Using a Session object that reuses underlying TCP connections
        self.session = requests.Session()
        # MUST observe a politeness window of at least 6 seconds
        self.politeness_delay = 6.0 

    def fetch_page(self, url, retries=3):
        """
        Fetches a web page with strict politeness delays and robust error handling.
        Implements exponential backoff for failed requests.
        """
        for attempt in range(retries):
            try:
                print(f"Crawling: {url} (Waiting {self.politeness_delay}s to respect server...)")
                time.sleep(self.politeness_delay)
                
                # Fetch the page with a timeout to prevent hanging indefinitely
                response = self.session.get(url, timeout=10)
                response.raise_for_status() # Raises HTTPError for bad responses (404, 500, etc.)
                return response.text
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    # Exponential backoff: Wait longer on subsequent failures (6s -> 12s)
                    backoff = self.politeness_delay * (attempt + 2)
                    print(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    print(f"Failed to fetch {url} after {retries} attempts. Skipping.")
                    return None

    def extract_next_url(self, html, current_url):
        """
        Parses the HTML to find the 'Next' button for pagination.
        """
        soup = BeautifulSoup(html, 'html.parser')
        next_li = soup.select_one('li.next a')
        
        if next_li and 'href' in next_li.attrs:
            # urljoin safely handles relative URLs (e.g., turning '/page/2/' into 'https://site.com/page/2/')
            return urljoin(current_url, next_li['href'])
        return None

    def extract_page_text(self, html):
        """
        Extracts the meaningful text from the page (quotes and authors).
        """
        soup = BeautifulSoup(html, 'html.parser')
        quotes = soup.find_all('div', class_='quote')
        
        extracted_text = []
        for quote in quotes:
            text = quote.find('span', class_='text').get_text(strip=True)
            author = quote.find('small', class_='author').get_text(strip=True)
            extracted_text.append(f"{text} {author}")
            
        return " ".join(extracted_text)

# --- Quick Test Block ---
if __name__ == '__main__':
    crawler = WebCrawler()
    
    # Test fetching the first page
    html = crawler.fetch_page(crawler.base_url)
    
    if html:
        text = crawler.extract_page_text(html)
        next_page = crawler.extract_next_url(html, crawler.base_url)
        
        print("\n--- Test Results ---")
        print(f"Extracted Text Snippet: {text[:100]}...")
        print(f"Next Page URL found: {next_page}")