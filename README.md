## Repository Structure

```
COMP3011_CwK_2/
├── .github/
│   └── workflows/
│       └── python-app.yml     # (Stretch Feature) Automated testing pipeline for the 80-100 band
├── data/
│   └── .gitkeep               # Keeps the empty folder in Git. Your SQLite index will save here.
├── src/
│   ├── __init__.py            # Makes the src directory a discoverable Python package
│   ├── crawler.py             # Handles the 6-second politeness window and HTML fetching
│   ├── indexer.py             # Parses HTML and builds the SQLite inverted index
│   ├── search.py              # Contains the ranking logic (Frequency/TF-IDF)
│   └── main.py                # The Command-Line Interface (build, load, print, find)
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # We will put our pytest fixtures (like the memory DB) in here
│   ├── test_crawler.py        # Mocks network requests
│   ├── test_indexer.py        # Tests text normalisation and DB insertion
│   └── test_search.py         # Benchmarks the TF-IDF and frequency algorithms
├── .gitignore                 # Crucial: prevents committing cache files and massive databases
├── requirements.txt           # Lists dependencies (requests, beautifulsoup4, pytest, pytest-mock)
└── README.md                  # Comprehensive documentation, setup instructions, and complexity analysis
```
