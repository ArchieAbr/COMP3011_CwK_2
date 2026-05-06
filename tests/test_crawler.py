import pytest
from src.crawler import WebCrawler
import requests

def test_extract_page_text():
    """Tests if the BeautifulSoup parser correctly extracts quotes and authors."""
    crawler = WebCrawler()
    # Provide fake HTML directly to the function
    fake_html = '''
    <div class="quote">
        <span class="text">"A test quote."</span>
        <small class="author">Test Author</small>
    </div>
    '''
    result = crawler.extract_page_text(fake_html)
    assert result == '"A test quote." Test Author'

def test_extract_next_url_finds_link():
    """Tests if the pagination parser correctly finds the next page URL."""
    crawler = WebCrawler()
    fake_html = '<li class="next"><a href="/page/2/">Next</a></li>'
    
    result = crawler.extract_next_url(fake_html, "http://fake-site.com")
    assert result == "http://fake-site.com/page/2/"

def test_fetch_page_success(mocker):
    """
    Mocks the requests.Session.get call to simulate a successful 
    server response without waiting 6 seconds.
    """
    crawler = WebCrawler()
    crawler.politeness_delay = 0  # Override delay just for test speed
    
    # 1. Intercept the 'get' method of requests.Session
    mock_get = mocker.patch('requests.Session.get')
    
    # 2. Define what the intercepted call should return
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html>Success</html>"
    
    # 3. Call our crawler function
    html = crawler.fetch_page("http://fake-site.com")
    
    # 4. Assert it worked correctly
    assert html == "<html>Success</html>"
    mock_get.assert_called_once_with("http://fake-site.com", timeout=10)

def test_fetch_page_retries_on_failure(mocker):
    """
    Tests the graceful error recovery. Simulates network failures to ensure
    the crawler attempts retries before giving up.
    """
    crawler = WebCrawler()
    crawler.politeness_delay = 0  # Override delay for test speed
    
    # Force the mock to raise a simulated network error every time it is called
    mock_get = mocker.patch('requests.Session.get', side_effect=requests.exceptions.ConnectionError)
    # Mock the time.sleep
    mock_sleep = mocker.patch('time.sleep') 
    
    # Call the crawler with 2 retries
    html = crawler.fetch_page("http://fake-site.com", retries=2)
    
    # Assert it returned None (failed gracefully) and tried exactly twice
    assert html is None
    assert mock_get.call_count == 2


def test_extract_next_url_returns_none_on_last_page():
    """Tests that extract_next_url returns None when there is no 'Next' button (final page)."""
    crawler = WebCrawler()
    # HTML with no pagination element at all
    fake_html = '<div class="quote"><span class="text">A quote.</span></div>'
    result = crawler.extract_next_url(fake_html, "http://fake-site.com/page/10/")
    assert result is None


def test_extract_page_text_multiple_quotes():
    """Tests that extract_page_text correctly concatenates text from multiple quote divs."""
    crawler = WebCrawler()
    fake_html = '''
    <div class="quote">
        <span class="text">"First quote."</span>
        <small class="author">Author One</small>
    </div>
    <div class="quote">
        <span class="text">"Second quote."</span>
        <small class="author">Author Two</small>
    </div>
    '''
    result = crawler.extract_page_text(fake_html)
    assert '"First quote." Author One' in result
    assert '"Second quote." Author Two' in result


def test_fetch_page_http_error_triggers_retry(mocker):
    """Tests that a non-2xx HTTP response (e.g. 404) triggers the retry mechanism."""
    crawler = WebCrawler()
    crawler.politeness_delay = 0

    # raise_for_status raises HTTPError for bad status codes
    mock_response = mocker.MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mocker.patch('requests.Session.get', return_value=mock_response)
    mocker.patch('time.sleep')

    html = crawler.fetch_page("http://fake-site.com", retries=2)

    assert html is None