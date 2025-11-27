# Debugging pytest Tests

This guide covers various ways to debug your pytest tests.

## Method 1: Using `breakpoint()` (Recommended for Cursor/VS Code)

Add `breakpoint()` directly in your test code where you want to pause:

```python
def test_get_endpoint(self):
    """Test GET endpoint with Pythonic validation."""
    response = self.authenticated_request.get("/my/endpoint")
    
    breakpoint()  # Execution will pause here
    
    # Fluent validation API
    response.should_have.status_code(200)
```

Then run pytest with output capture disabled:
```bash
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -s
```

The debugger will drop into Python's built-in debugger (pdb). Common commands:
- `n` (next line)
- `s` (step into)
- `c` (continue)
- `p variable_name` (print variable)
- `pp variable_name` (pretty print)
- `l` (list code)
- `q` (quit)

## Method 2: Drop into Debugger on Failure

Automatically drop into debugger when a test fails:

```bash
# Drop into debugger on failure
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --pdb

# Drop into debugger on error (before teardown)
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --pdbcls=IPython.terminal.debugger:Pdb
```

## Method 3: Drop into Debugger at Test Start

Drop into debugger at the very beginning of the test:

```bash
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --trace
```

## Method 4: Verbose Output and Tracebacks

Get detailed information about what's happening:

```bash
# Very verbose output
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -vv

# Show print statements (disable output capture)
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -s

# Show local variables in traceback
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --tb=long

# Show only failed assertions
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --tb=short

# Show no traceback (just summary)
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --tb=no
```

## Method 5: Using Cursor/VS Code Debugger

1. **Create a debug configuration** (`.vscode/launch.json`):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Pytest Current File",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${file}",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Pytest All Tests",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Pytest Specific Test",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/example_test.py::TestExampleAPI::test_get_endpoint",
                "-v",
                "-s"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

2. **Set breakpoints** in your code by clicking in the gutter (left of line numbers)

3. **Run the debugger**:
   - Press `F5` or click the Run and Debug icon
   - Select the configuration you want
   - Execution will pause at breakpoints

## Method 6: Logging and Print Statements

Since the framework has logging built-in, you can use it:

```python
import logging

logger = logging.getLogger(__name__)

def test_get_endpoint(self):
    """Test GET endpoint with Pythonic validation."""
    logger.debug("About to make request")
    response = self.authenticated_request.get("/my/endpoint")
    logger.debug(f"Response status: {response.response.status}")
    logger.debug(f"Response body: {response.extract.as_string()}")
    
    response.should_have.status_code(200)
```

Run with debug logging:
```bash
# Set log level to DEBUG in .env or:
LOG_LEVEL=DEBUG pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -s
```

## Method 7: Inspect Response Objects

Add inspection code in your test:

```python
def test_get_endpoint(self):
    """Test GET endpoint with Pythonic validation."""
    response = self.authenticated_request.get("/my/endpoint")
    
    # Inspect the response
    print(f"Status: {response.response.status}")
    print(f"Headers: {dict(response.response.headers)}")
    print(f"Body: {response.extract.as_string()}")
    
    # Or use breakpoint to inspect interactively
    breakpoint()
    
    response.should_have.status_code(200)
```

## Method 8: Check Log Files

The framework automatically logs all requests/responses. Check the log files:

```bash
# Find the latest log file
ls -lt logs/ | head -2

# View the log
tail -f logs/api_test_*.log
```

## Quick Reference

```bash
# Most common debugging command
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -s --pdb

# Run with full output and drop into debugger on failure
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint -vv -s --pdb --tb=long

# Run specific test with trace (stops at first line)
pytest tests/example_test.py::TestExampleAPI::test_get_endpoint --trace -s
```

## Tips

1. **Use `-s` flag** to see print statements and logging output
2. **Use `--pdb`** to automatically debug on failures
3. **Check log files** in `logs/` directory for detailed request/response logs
4. **Set `LOG_LEVEL=DEBUG`** in `.env` for more verbose logging
5. **Use breakpoint()** for interactive debugging in Cursor/VS Code

