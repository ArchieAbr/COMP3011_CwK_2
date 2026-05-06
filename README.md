# COMP3011 Coursework 2 — Web Search Engine

A command-line web search engine that crawls [quotes.toscrape.com](https://quotes.toscrape.com/), builds a persistent SQLite inverted index, and supports TF-IDF ranked search with exact phrase matching.

---

## Repository Structure

```
COMP3011_CwK_2/
├── .github/
│   └── workflows/
│       └── python-app.yml     # Automated CI testing pipeline (GitHub Actions)
├── data/
│   └── .gitkeep               # Keeps the empty folder tracked by Git; the SQLite index is saved here
├── src/
│   ├── __init__.py            # Makes src a discoverable Python package
│   ├── crawler.py             # Fetches web pages with a politeness delay and pagination support
│   ├── indexer.py             # Parses page text and builds the SQLite inverted index
│   ├── search.py              # TF-IDF ranking and exact phrase matching logic
│   └── main.py                # Interactive command-line shell (build, load, print, find)
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared pytest fixtures (in-memory databases)
│   ├── test_crawler.py        # Unit tests for crawling and pagination, with mocked HTTP calls
│   ├── test_indexer.py        # Unit tests for text normalisation and database insertion
│   ├── test_main.py           # Unit tests for the interactive shell (all commands)
│   └── test_search.py         # Unit tests for TF-IDF ranking and phrase matching
├── .gitignore                 # Prevents committing cache files and generated databases
├── requirements.txt           # Project dependencies
└── README.md                  # This file
```

---

## Getting Started

### Prerequisites

- Python 3.10 or later

### Installation

```bash
pip install -r requirements.txt
```

### Running the Search Engine

```bash
python -m src.main
```

This opens an interactive shell. The available commands are:

| Command           | Description                                               |
| ----------------- | --------------------------------------------------------- |
| `build`           | Crawls the website and builds the SQLite index in `data/` |
| `load`            | Loads the saved index from `data/` into memory            |
| `print <word>`    | Displays the inverted index entry for a given word        |
| `find <query>`    | Searches the index and returns results ranked by TF-IDF   |
| `find "<phrase>"` | Searches for an exact phrase (wrap in double quotes)      |
| `exit` / `quit`   | Exits the shell                                           |

### Running the Tests

```bash
pytest -v --cov=src --cov-report=term-missing
```

---

## File-by-File Breakdown

### `src/crawler.py` — Web Crawler

The `WebCrawler` class is responsible for fetching and parsing pages from `quotes.toscrape.com`.

- **Politeness delay:** Waits at least 6 seconds between every HTTP request to avoid overloading the server. This is enforced inside `fetch_page` before every request.
- **Retry logic:** If a request fails, the crawler retries up to 3 times using exponential backoff (e.g. 6 s → 12 s between attempts). If all retries are exhausted, `None` is returned so the caller can handle the failure gracefully.
- **Session reuse:** Uses a `requests.Session` object to reuse the underlying TCP connection across requests, which is more efficient than opening a new connection for each page.
- **`fetch_page(url, retries=3)`** — Fetches the raw HTML for a given URL, enforcing the politeness delay and retry logic.
- **`extract_next_url(html, current_url)`** — Parses the HTML using BeautifulSoup to find the pagination "Next" button and returns the absolute URL of the next page, or `None` if there is no next page. Uses `urljoin` to safely resolve relative URLs.
- **`extract_page_text(html)`** — Extracts the meaningful text content from a page: the quote text and author name from each quote `<div>`. Navigation links, tags, and other boilerplate are discarded.

---

### `src/indexer.py` — Inverted Index Builder

Handles all interaction with the SQLite database and the construction of the inverted index.

**Database schema:**

- `inverted_index` table — Stores one row per `(word, url)` pair, recording the term frequency and a JSON-encoded list of character positions where the word appears.
- `metadata` table — Stores corpus-wide statistics. Currently tracks `total_documents`, which is required by the TF-IDF formula.

**Key functions:**

- **`get_db_connection(db_name)`** — Opens a connection to the specified SQLite database inside the `data/` directory. The path is resolved relative to the source file so the engine works from any working directory.
- **`initialise_database(conn)`** — Creates the `inverted_index` and `metadata` tables if they do not already exist, and adds a word index on `inverted_index` for fast lookups.
- **`normalise_text(text)`** — Converts text to lowercase and strips all punctuation using a regular expression, then splits it into a list of tokens. This ensures that words like "Hello," and "hello" are treated identically.
- **`index_page(conn, url, raw_text)`** — The main indexing function. It normalises the raw page text, calculates the frequency and positional list for every word, and writes the results to the database using a batch `executemany`. It also increments the `total_documents` counter in the `metadata` table.

---

### `src/search.py` — Search and Ranking

Implements the query execution pipeline on top of the inverted index.

- **`get_total_documents(conn)`** — Reads the `total_documents` value from the `metadata` table for use in IDF calculations.
- **`get_word_index(conn, word)`** — Returns the full inverted index entry for a single word (URL, frequency, and positions), ordered by frequency descending. Used by the `print` command in the shell.
- **`search_query(conn, query_string)`** — The main search function. It performs the following steps:
  1. **Exact phrase detection** — If the query string is wrapped in double quotes, exact phrase mode is activated before the quotes are stripped by normalisation.
  2. **Normalisation** — The query is lowercased and stripped of punctuation to match the format stored in the index.
  3. **Boolean AND filtering** — Only URLs that contain _every_ word in the query are considered. Any URL missing even one query term is discarded.
  4. **Exact phrase verification** — If exact phrase mode is active, the positional lists are checked to confirm that the words appear consecutively in the correct order.
  5. **TF-IDF scoring** — Each candidate URL is scored. Term Frequency (TF) is the number of times a word appears in that document. Inverse Document Frequency (IDF) is calculated as $\log_{10}(\frac{N}{df})$, where $N$ is the total number of documents and $df$ is the number of documents containing that word. Common words across many pages receive a low IDF, reducing their contribution to the score.
  6. **Ranking** — Results are sorted by descending TF-IDF score before being returned.

---

### `src/main.py` — Command-Line Interface

Provides the interactive shell using Python's built-in `cmd.Cmd` base class.

The `SearchEngineShell` class defines one method per command (`do_build`, `do_load`, `do_print`, `do_find`, `do_exit`). The `cmd` module automatically maps the user's input to the corresponding method and populates the built-in `help` command from each method's docstring.

- **`do_build`** — Creates a fresh database connection, initialises the schema, then runs the crawler in a loop. Each page fetched is immediately passed to `index_page`. The loop terminates when `extract_next_url` returns `None` (no more pages) or a fetch fails.
- **`do_load`** — Opens a connection to the saved `index.sqlite` database and stores it on `self.conn` for use by subsequent commands.
- **`do_print`** — Calls `get_word_index` and prints each matching row (URL, frequency, and positions) to the terminal.
- **`do_find`** — Passes the raw query string (including any surrounding double quotes) to `search_query` and prints the ranked results with their TF-IDF scores.

---

### `tests/conftest.py` — Pytest Fixtures

Defines two shared fixtures used across the test suite:

- **`empty_db`** — Creates a transient, in-memory SQLite database (`:memory:`) with the correct schema applied. Using an in-memory database means tests run fast and leave no files on disk.
- **`populated_db`** — Builds on `empty_db` by inserting three carefully chosen test documents designed to exercise the TF-IDF logic (one document spams the word "the" to demonstrate IDF penalisation of common terms).

---

### `tests/test_crawler.py` — Crawler Tests

- **`test_extract_page_text`** — Provides a hand-crafted HTML string directly to `extract_page_text` and asserts the correct text is returned, without making any network calls.
- **`test_extract_next_url_finds_link`** — Verifies that the pagination parser correctly resolves a relative `href` into an absolute URL.
- **`test_extract_next_url_returns_none_on_last_page`** — Verifies that `extract_next_url` returns `None` when no pagination element is present (i.e. the final page).
- **`test_extract_page_text_multiple_quotes`** — Confirms that text from multiple quote `<div>` elements is concatenated correctly into a single string.
- **`test_fetch_page_success`** — Uses `pytest-mock` to intercept `requests.Session.get` and return a fake 200 response. The politeness delay is set to zero so the test runs instantly.
- **`test_fetch_page_retries_on_failure`** — Configures the mock to raise a `ConnectionError` on every call and verifies that the crawler attempts the request the correct number of times before returning `None`.
- **`test_fetch_page_http_error_triggers_retry`** — Configures `raise_for_status` to raise an `HTTPError` (simulating a 404) and verifies the retry mechanism is triggered.

---

### `tests/test_indexer.py` — Indexer Tests

- **`test_normalise_text_removes_punctuation`** — Asserts that a string with mixed-case letters and punctuation is correctly converted to a list of lowercase tokens.
- **`test_normalise_text_empty_string`** — Asserts that normalising an empty string returns an empty list rather than raising an exception.
- **`test_normalise_text_preserves_numbers`** — Confirms that numeric characters are retained after normalisation.
- **`test_index_page_inserts_data`** — Indexes a short string and queries the database directly to verify that word frequencies and positional lists are stored accurately.
- **`test_index_page_updates_metadata`** — Indexes two separate pages and confirms that the `total_documents` counter in the `metadata` table increments to 2.
- **`test_index_page_updates_existing_word_on_reindex`** — Verifies the `INSERT OR REPLACE` behaviour: re-indexing the same URL updates the existing `(word, url)` row rather than inserting a duplicate.

---

### `tests/test_search.py` — Search Tests

- **`test_search_boolean_and_logic`** — Queries for two words that appear in different documents and asserts that no results are returned (Boolean AND requirement).
- **`test_search_tfidf_ranking`** — Queries for "the fox" and asserts that the correct page is returned with a positive score, demonstrating that TF-IDF correctly handles a mix of common and rare terms.
- **`test_search_tfidf_orders_multiple_results`** — Asserts that when multiple pages match a query, results are returned in descending score order.
- **`test_search_exact_phrase_matching_success`** — Verifies that a quoted phrase query returns all pages that contain the words consecutively.
- **`test_search_exact_phrase_matching_failure`** — Verifies that a quoted phrase returns no results when the words exist in the index but not in the queried order.
- **`test_search_single_word_exact_phrase`** — Confirms that a single word wrapped in quotes returns the same URLs as the same word without quotes.
- **`test_search_empty_query`** — Asserts that an empty or whitespace-only query returns an empty list without raising an exception.
- **`test_search_returns_empty_when_no_documents`** — Asserts that searching an empty index returns an empty list rather than causing a division-by-zero error.
- **`test_get_word_index_returns_empty_for_unknown_word`** — Confirms that `get_word_index` returns an empty list for a word not present in the index.

---

### `tests/test_main.py` — Shell Tests

Tests the `SearchEngineShell` class in isolation by injecting in-memory databases and mocking the crawler and filesystem dependencies. Covers all five commands.

**Guard tests** — commands invoked in the wrong state:

- **`test_do_find_requires_load`** / **`test_do_print_requires_load`** — Verify that both commands print an error message when called before `load`.
- **`test_do_find_requires_argument`** / **`test_do_print_requires_argument`** — Verify that both commands print a usage error when called with no argument.

**`do_load` tests:**

- **`test_do_load_success`** — Mocks `get_db_connection` and asserts that `self.conn` is set and a success message is printed.
- **`test_do_load_failure`** — Mocks `get_db_connection` to raise an exception and asserts that `self.conn` remains `None` and an error is printed.

**`do_find` tests:**

- **`test_do_find_returns_ranked_results`** — Asserts that a matching query produces scored, numbered output.
- **`test_do_find_no_matching_results`** — Asserts that an unmatched query prints a "No pages found" message.
- **`test_do_find_exact_phrase`** — Confirms that a double-quoted query is passed through to the search engine correctly.
- **`test_do_find_results_are_numbered`** — Confirms the output contains a numbered ranking list.

**`do_print` tests:**

- **`test_do_print_known_word`** — Asserts that a known word’s URL, frequency, and positions are all displayed.
- **`test_do_print_unknown_word`** — Asserts that a missing word produces a “not found” message.
- **`test_do_print_is_case_insensitive`** — Confirms that uppercase input is normalised before querying.

**`do_exit` / `do_quit` tests:**

- **`test_do_exit_returns_true`** — Confirms `do_exit` returns `True` to signal `cmd.Cmd` to stop the loop.
- **`test_do_exit_closes_open_connection`** — Asserts that the database connection is closed when one is active.
- **`test_do_exit_without_connection_does_not_raise`** — Confirms no exception is raised when exiting without a loaded index.
- **`test_do_quit_is_alias_for_exit`** — Confirms `do_quit` behaves identically to `do_exit`.

**`do_build` tests:**

- **`test_do_build_single_page`** — Mocks the crawler to return one page and confirms that `index_page` is called once and the database connection is closed.
- **`test_do_build_multi_page`** — Configures the mock to paginate across two pages and confirms `index_page` is called twice.
- **`test_do_build_stops_on_failed_fetch`** — Simulates a fetch failure and confirms the build loop halts cleanly with a warning, without calling `index_page`.

---

### `.github/workflows/python-app.yml` — CI Pipeline

A GitHub Actions workflow that runs automatically on every push or pull request to the `main` branch. It spins up an Ubuntu runner, installs Python 3.10, installs the project dependencies from `requirements.txt`, and then runs the full test suite with coverage reporting enabled (`pytest -v --cov=src --cov-report=term-missing`). The coverage summary is printed directly in the pipeline log, showing which lines in `src/` are not yet exercised by the test suite.

---

## Complexity Analysis

### Crawl Phase

The crawler visits each page exactly once and follows pagination links linearly. For a site with $P$ pages, the crawl is $O(P)$ in time. The dominant cost is not computation but network I/O, specifically the mandatory 6-second politeness delay per request, making wall-clock time approximately $6P$ seconds regardless of page size.

Memory usage is $O(1)$ per page because each page is fetched, processed, and discarded before the next request is issued. The engine never holds more than one page in memory at a time.

---

### Index Build Phase

Let $W$ be the total number of word tokens across all pages and $V$ be the vocabulary size (unique words).

| Step                                  | Complexity    | Notes                                                         |
| ------------------------------------- | ------------- | ------------------------------------------------------------- |
| Text normalisation (`normalise_text`) | $O(W)$        | Single pass: lowercase + regex strip + split                  |
| Frequency and position counting       | $O(W)$        | One dictionary lookup per token                               |
| Batch database insert (`executemany`) | $O(V \log V)$ | SQLite B-tree insert per unique word; one round-trip per page |

**Optimisation — batch inserts:** The naïve approach would be to call `cursor.execute` once per word, incurring $V$ individual round-trips to the SQLite engine. Using `executemany` batches all rows for a page into a single call, reducing overhead substantially when $V$ is large.

**Optimisation — SQL index on `word`:** After the build is complete, the `idx_word` index on the `inverted_index` table stores the words in a B-tree structure. This brings lookup time during queries from $O(V)$ (full table scan) down to $O(\log V)$.

Overall build complexity per page: $O(W + V \log V)$. Across all $P$ pages: $O(P \cdot (W_{\text{avg}} + V_{\text{avg}} \log V_{\text{avg}}))$.

---

### Query Phase

Let $Q$ be the number of unique terms in the query, $D$ be the number of candidate documents (URLs that contain at least one query term), and $V$ be the vocabulary size.

| Step                                  | Complexity                  | Notes                                                                        |
| ------------------------------------- | --------------------------- | ---------------------------------------------------------------------------- |
| Normalise query                       | $O(Q)$                      | Identical pipeline to index build                                            |
| Document frequency lookup (per term)  | $O(Q \log V)$               | One B-tree lookup per term via `idx_word`                                    |
| Fetch all candidate rows              | $O(Q \log V + D \cdot Q)$   | Single `WHERE word IN (...)` query; results grouped by URL in Python         |
| Boolean AND filter                    | $O(D \cdot Q)$              | Check that each URL contains all $Q$ terms                                   |
| Exact phrase verification (if active) | $O(D \cdot P_{\text{avg}})$ | $P_{\text{avg}}$ = average positions list length; checks consecutive offsets |
| TF-IDF scoring                        | $O(D \cdot Q)$              | One multiply-and-add per (document, term) pair                               |
| Sort results                          | $O(D \log D)$               | Python's Timsort on the scored results list                                  |

**Optimisation — single batched SQL query:** A naïve implementation would issue one `SELECT` per query term, costing $O(Q)$ round-trips to SQLite. Instead, all terms are fetched in a single `WHERE word IN (?, ?, ...)` statement, reducing database round-trips to one regardless of $Q$.

**Optimisation — pre-computed document frequency:** Document frequency values (`df`) for each query term are fetched upfront in a separate pass and cached in a dictionary before the scoring loop begins. This avoids issuing a fresh `COUNT` query inside the inner scoring loop, keeping the scoring step at $O(D \cdot Q)$ rather than $O(D \cdot Q^2)$.

Overall query complexity: $O(Q \log V + D \cdot Q + D \log D)$. In practice $D \ll V$, so the B-tree lookups ($O(Q \log V)$) and sorting ($O(D \log D)$) dominate.

---

## Dependencies

| Package          | Version | Purpose                                                 |
| ---------------- | ------- | ------------------------------------------------------- |
| `requests`       | 2.31.0  | HTTP client for fetching web pages                      |
| `beautifulsoup4` | 4.12.3  | HTML parsing for text and link extraction               |
| `pytest`         | 8.1.1   | Test framework                                          |
| `pytest-mock`    | 3.14.0  | Mocking library for intercepting network calls in tests |
| `pytest-cov`     | 5.0.0   | Coverage reporting plugin for pytest                    |
