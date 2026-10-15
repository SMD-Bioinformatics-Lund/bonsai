# Bonsai GUI

This is the frontend of the Bonsai application.

Run the focused overview checks from this directory with the existing Python
test environment and npm dependencies:

```sh
PYTHONPATH=. pytest tests/test_overview_data.py tests/test_summary_columns.py
node --test tests/test_overview_table.cjs
npm run typecheck
```
