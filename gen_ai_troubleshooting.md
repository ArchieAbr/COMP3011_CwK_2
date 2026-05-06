### Bug 1: ModuleNotFoundError for 'src'

**The Problem:**
When testing the search logic, the application crashed with a `ModuleNotFoundError: No module named 'src'`. This occurred on the line `from src.indexer import normalise_text` inside `src/search.py`. This was caused by executing the script directly (`python src/search.py`), which alters Python's `sys.path`. Python treated the `src/` directory as the project root, causing absolute imports starting with `src.` to fail.

**The Solution:**
Instead of modifying the import statements to relative paths (which can cause further routing issues), the execution method was corrected. The script was executed as a module from the actual project root using the `-m` flag (`python -m src.search`). This preserved the correct directory structure in Python's pathing, allowing the absolute imports to resolve correctly.

### Bug 2: Shared Setup Code Lost When Removing a Notebook Section

**The Problem:**
After removing Benchmark 1 (SQL Index) from `benchmark.ipynb`, the remaining benchmarks raised `NameError: name 'page_data' is not defined` and `NameError: name 'plt' is not defined`. The removed section had contained a setup cell that built the `page_data` list used by the insert benchmark, and a chart cell that imported `matplotlib.pyplot as plt` relied on by both remaining chart cells. Because this setup was colocated with the benchmark being deleted rather than placed in the shared imports cell, removing one section silently broke the others.

**The Solution:**
`import matplotlib.pyplot as plt` was moved into the top-level imports cell so it is always available. A setup was added to construct `page_data`, making the shared data explicit and independent of any individual benchmark section. Shared state (imports, fixtures) should always live in cells that precede all benchmarks, not inside a specific section that may later be removed.
