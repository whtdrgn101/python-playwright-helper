# Installation Guide

## Installing Playwright

Playwright requires two steps:
1. Install the Python package
2. Install the browser binaries

### Step 1: Install Python Package

```bash
# Using UV (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

This will install the `playwright` Python package along with other dependencies.

### Step 2: Install Browser Binaries

After installing the Python package, install the browser binaries:

```bash
# Using Python module (recommended)
python3 -m playwright install

# Or if playwright command is in PATH
playwright install

# Install only specific browsers (lighter weight)
python3 -m playwright install chromium
```

### Troubleshooting

#### Issue: "playwright: command not found"

**Solution:** Use the Python module instead:
```bash
python3 -m playwright install
```

#### Issue: Permission errors

**Solution:** Install with user permissions:
```bash
python3 -m playwright install --with-deps
```

Or install system dependencies first (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```

#### Issue: Network/firewall issues

**Solution:** Playwright downloads browsers from CDN. If behind a firewall:
```bash
# Set proxy if needed
export HTTPS_PROXY=http://your-proxy:port
python3 -m playwright install
```

#### Issue: Out of disk space

**Solution:** Browsers take ~500MB. Check space:
```bash
df -h
```

#### Alternative: Install without browsers (for API testing only)

If you're only doing API testing (not browser automation), you might not need all browsers:

```bash
# Install only what's needed for API testing
python3 -m playwright install chromium
```

### Verify Installation

```bash
# Check Playwright version
python3 -m playwright --version

# Check if browsers are installed
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright installed successfully')"
```

### For API Testing Only

**Note:** For REST API testing (which this framework does), you typically don't need the full browser binaries. However, Playwright's API testing still requires some system dependencies.

If you're having persistent issues, you can try:

1. **Install minimal dependencies:**
   ```bash
   python3 -m playwright install-deps chromium
   ```

2. **Use a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   uv pip install -e .
   python3 -m playwright install chromium
   ```

3. **Check system requirements:**
   - Python 3.9+
   - ~500MB free disk space
   - Network access for downloading browsers

### Quick Test

After installation, verify everything works:

```bash
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    print('✓ Playwright installed and working')
"
```

