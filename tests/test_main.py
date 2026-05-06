import pytest
from unittest.mock import MagicMock
from src.main import SearchEngineShell


# Fixtures

@pytest.fixture
def shell():
    """Provides a fresh, unloaded shell instance (no database connection)."""
    return SearchEngineShell()


@pytest.fixture
def loaded_shell(populated_db):
    """Provides a shell instance with a pre-populated in-memory database already attached."""
    instance = SearchEngineShell()
    instance.conn = populated_db
    return instance


# Guard tests — commands called before do_load

def test_do_find_requires_load(shell, capsys):
    """Verifies that do_find prints an error when called before do_load."""
    shell.do_find("brown fox")
    captured = capsys.readouterr()
    assert "Error" in captured.out
    assert "load" in captured.out


def test_do_print_requires_load(shell, capsys):
    """Verifies that do_print prints an error when called before do_load."""
    shell.do_print("fox")
    captured = capsys.readouterr()
    assert "Error" in captured.out
    assert "load" in captured.out


# Guard tests — commands called without a required argument

def test_do_find_requires_argument(loaded_shell, capsys):
    """Verifies that do_find prints a usage error when called with no query."""
    loaded_shell.do_find("")
    captured = capsys.readouterr()
    assert "Error" in captured.out


def test_do_print_requires_argument(loaded_shell, capsys):
    """Verifies that do_print prints a usage error when called with no word."""
    loaded_shell.do_print("")
    captured = capsys.readouterr()
    assert "Error" in captured.out


# do_load tests

def test_do_load_success(shell, mocker, capsys):
    """Verifies that do_load sets self.conn and prints a success message."""
    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)

    shell.do_load("")

    captured = capsys.readouterr()
    assert shell.conn is mock_conn
    assert "successfully" in captured.out


def test_do_load_failure(shell, mocker, capsys):
    """Verifies that do_load prints an error and leaves self.conn as None when the DB cannot be opened."""
    mocker.patch('src.main.get_db_connection', side_effect=Exception("disk I/O error"))

    shell.do_load("")

    captured = capsys.readouterr()
    assert "Error" in captured.out
    assert shell.conn is None


# do_find tests

def test_do_find_returns_ranked_results(loaded_shell, capsys):
    """Verifies that do_find outputs TF-IDF ranked results for a matching query."""
    loaded_shell.do_find("brown fox")
    captured = capsys.readouterr()
    assert "Score:" in captured.out
    assert "page2.com" in captured.out or "page3.com" in captured.out


def test_do_find_no_matching_results(loaded_shell, capsys):
    """Verifies that do_find reports no results when the query matches nothing."""
    loaded_shell.do_find("zzznomatchatall")
    captured = capsys.readouterr()
    assert "No pages found" in captured.out


def test_do_find_exact_phrase(loaded_shell, capsys):
    """Verifies that do_find correctly handles a quoted exact phrase query."""
    loaded_shell.do_find('"brown fox"')
    captured = capsys.readouterr()
    assert "Score:" in captured.out


def test_do_find_results_are_numbered(loaded_shell, capsys):
    """Verifies that do_find outputs a numbered ranking list."""
    loaded_shell.do_find("brown fox")
    captured = capsys.readouterr()
    assert "1." in captured.out


# do_print tests

def test_do_print_known_word(loaded_shell, capsys):
    """Verifies that do_print displays the full inverted index entry for a known word."""
    loaded_shell.do_print("fox")
    captured = capsys.readouterr()
    assert "fox" in captured.out
    assert "Frequency:" in captured.out
    assert "URL:" in captured.out


def test_do_print_unknown_word(loaded_shell, capsys):
    """Verifies that do_print reports gracefully when the word is not in the index."""
    loaded_shell.do_print("zzznomatch")
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_do_print_is_case_insensitive(loaded_shell, capsys):
    """Verifies that do_print normalises the input word to lowercase before querying."""
    loaded_shell.do_print("FOX")
    captured = capsys.readouterr()
    assert "Frequency:" in captured.out


# do_exit / do_quit tests

def test_do_exit_returns_true(shell):
    """Verifies that do_exit returns True, signalling cmd.Cmd to stop the loop."""
    assert shell.do_exit("") is True


def test_do_exit_closes_open_connection(loaded_shell):
    """Verifies that do_exit closes the database connection when one is open."""
    mock_conn = MagicMock()
    loaded_shell.conn = mock_conn
    loaded_shell.do_exit("")
    mock_conn.close.assert_called_once()


def test_do_exit_without_connection_does_not_raise(shell):
    """Verifies that do_exit handles the case where no connection has been opened."""
    result = shell.do_exit("")
    assert result is True


def test_do_quit_is_alias_for_exit(shell):
    """Verifies that do_quit behaves identically to do_exit."""
    assert shell.do_quit("") is True


# do_build tests

def test_do_build_single_page(shell, mocker, capsys):
    """Verifies that do_build orchestrates the crawler and indexer for a single-page crawl."""
    mock_crawler = MagicMock()
    mock_crawler.base_url = "http://fake.com/"
    mock_crawler.fetch_page.return_value = "<html>page</html>"
    mock_crawler.extract_page_text.return_value = "some quote author"
    mock_crawler.extract_next_url.return_value = None  # only one page; stop after first
    mocker.patch('src.main.WebCrawler', return_value=mock_crawler)

    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)
    mocker.patch('src.main.initialise_database')
    mock_index = mocker.patch('src.main.index_page')

    shell.do_build("")

    captured = capsys.readouterr()
    assert "Build complete" in captured.out
    assert "indexed 1 pages" in captured.out
    mock_index.assert_called_once()
    mock_conn.close.assert_called_once()


def test_do_build_multi_page(shell, mocker, capsys):
    """Verifies that do_build continues crawling across multiple pages until pagination ends."""
    mock_crawler = MagicMock()
    mock_crawler.base_url = "http://fake.com/"
    mock_crawler.fetch_page.return_value = "<html>page</html>"
    mock_crawler.extract_page_text.return_value = "some text"
    # return a second URL on the first call, then None to stop
    mock_crawler.extract_next_url.side_effect = ["http://fake.com/page/2/", None]
    mocker.patch('src.main.WebCrawler', return_value=mock_crawler)

    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)
    mocker.patch('src.main.initialise_database')
    mock_index = mocker.patch('src.main.index_page')

    shell.do_build("")

    captured = capsys.readouterr()
    assert "indexed 2 pages" in captured.out
    assert mock_index.call_count == 2


def test_do_build_stops_on_failed_fetch(shell, mocker, capsys):
    """Verifies that do_build stops gracefully and prints a warning when a page fetch fails."""
    mock_crawler = MagicMock()
    mock_crawler.base_url = "http://fake.com/"
    mock_crawler.fetch_page.return_value = None  # simulate a total fetch failure
    mocker.patch('src.main.WebCrawler', return_value=mock_crawler)

    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)
    mocker.patch('src.main.initialise_database')
    mock_index = mocker.patch('src.main.index_page')

    shell.do_build("")

    captured = capsys.readouterr()
    assert "Warning" in captured.out
    mock_index.assert_not_called()
    mock_conn.close.assert_called_once()


    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)
    mocker.patch('src.main.initialise_database')
    mock_index = mocker.patch('src.main.index_page')

    shell.do_build("")

    captured = capsys.readouterr()
    assert "indexed 2 pages" in captured.out
    assert mock_index.call_count == 2


def test_do_build_stops_on_failed_fetch(shell, mocker, capsys):
    """Verifies that do_build stops gracefully and prints a warning when a page fetch fails."""
    mock_crawler = MagicMock()
    mock_crawler.base_url = "http://fake.com/"
    mock_crawler.fetch_page.return_value = None  # Simulate a total fetch failure
    mocker.patch('src.main.WebCrawler', return_value=mock_crawler)

    mock_conn = MagicMock()
    mocker.patch('src.main.get_db_connection', return_value=mock_conn)
    mocker.patch('src.main.initialise_database')
    mock_index = mocker.patch('src.main.index_page')

    shell.do_build("")

    captured = capsys.readouterr()
    assert "Warning" in captured.out
    mock_index.assert_not_called()
    mock_conn.close.assert_called_once()
