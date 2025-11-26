# REST API Testing Framework (Python)

This is a standalone Python package for REST API testing, extracted from the Java project.

## Location

The project is now located at: `/home/tim/dev/rest-api-testing-python`

## Quick Start

1. **Install dependencies:**
   ```bash
   cd /home/tim/dev/rest-api-testing-python
   uv pip install -e .
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

3. **Configure:**
   ```bash
   cp application.properties.example application.properties
   # Edit application.properties with your settings
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Next Steps

- Initialize git repository: `git init`
- Add remote: `git remote add origin <your-repo-url>`
- Create initial commit
- Set up CI/CD pipeline
- Publish to ProGet when ready

## Project Structure

```
rest-api-testing-python/
├── rest_api_testing/      # Main package
├── templates/             # Jinja2 templates
├── tests/                 # Test files
├── scripts/               # Deployment scripts
├── pyproject.toml        # Package configuration
└── README.md             # Full documentation
```

See `README.md` for complete documentation.

