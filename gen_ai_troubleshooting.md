### Bug 1: ModuleNotFoundError for 'src'

**The Problem:**
When testing the search logic, the application crashed with a `ModuleNotFoundError: No module named 'src'`. This occurred on the line `from src.indexer import normalise_text` inside `src/search.py`. This was caused by executing the script directly (`python src/search.py`), which alters Python's `sys.path`. Python treated the `src/` directory as the project root, causing absolute imports starting with `src.` to fail.

**The Solution:**
Instead of modifying the import statements to relative paths (which can cause further routing issues), the execution method was corrected. The script was executed as a module from the actual project root using the `-m` flag (`python -m src.search`). This preserved the correct directory structure in Python's pathing, allowing the absolute imports to resolve correctly.

