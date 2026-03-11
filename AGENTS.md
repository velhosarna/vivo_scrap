# AGENTS.md - Vivo Gestão Scraping & Monitoring

## Project Overview

This is a Python automation project that scrapes internet consumption data from the Vivo Gestão Empresas portal. It uses Playwright for browser automation, BeautifulSoup4 for HTML parsing, and SQLite3 for local data storage.

## Tech Stack

- **Python 3.x**
- **Playwright** - Browser automation (Chromium)
- **BeautifulSoup4** - HTML parsing
- **SQLite3** - Local database
- **Logging** - Event and error logging

## Build & Test Commands

### Installation
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies using uv
uv pip install playwright beautifulsoup4 pytest pytest-cov

# Install Playwright browsers
playwright install chromium
```

### Running the Application
```bash
uv run python main.py
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_scraper.py

# Run a single test function
uv run pytest tests/test_scraper.py::test_login_success

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

### Linting & Type Checking
```bash
# Linting with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/

# Format code
ruff format src/ tests/

# All checks together
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/
```

## Code Style Guidelines

### General Principles
- Follow PEP 8 style guide for Python
- Use meaningful, descriptive names for variables, functions, and classes
- Keep functions small and focused (single responsibility)
- Write docstrings for all public functions and classes
- Type hints are required for function signatures

### Imports
```python
# Standard library imports first
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

# Third-party imports second
from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup

# Local imports last (with relative imports)
from .database import Database
from .models import UsageData
```

### Naming Conventions
- **Variables**: `snake_case` (e.g., `user_name`, `cota_grupo`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `TIMEOUT`)
- **Functions**: `snake_case` (e.g., `get_usage_data()`, `parse_html()`)
- **Classes**: `PascalCase` (e.g., `Scraper`, `DatabaseManager`)
- **Files**: `snake_case` (e.g., `scraper.py`, `database_utils.py`)

### Formatting
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Add blank lines between function definitions (2 lines)
- Add blank lines between class definitions (2 lines)
- Use f-strings for string formatting

### Type Hints
```python
# Good
def get_user_data(user_id: int) -> Optional[dict]:
    pass

def process_usage(usage_list: list[UsageData]) -> dict[str, float]:
    pass

# Avoid
def get_user_data(user_id):
    pass
```

### Error Handling
- Use specific exception types
- Log errors before re-raising or handling
- Never expose credentials in error messages
- Use try/except blocks sparingly and specifically

```python
# Good
try:
    page.goto(url, timeout=30000)
except TimeoutError as e:
    logger.error(f"Timeout loading page: {url}")
    raise ScrapingError(f"Failed to load {url}") from e

# Avoid bare except
try:
    page.goto(url)
except:
    pass
```

### Database Operations (SQLite3)
- Use parameterized queries to prevent SQL injection
- Always close connections (use context managers)
- Use `?` placeholder for SQLite (not `%s` like MySQL)

```python
# Good
conn = sqlite3.connect('vivo_gestao.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM filial WHERE grupo = ?", (grupo,))
results = cursor.fetchall()
conn.close()

# Better - use context manager
with sqlite3.connect('vivo_gestao.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM filial WHERE grupo = ?", (grupo,))
    return cursor.fetchall()
```

### Logging
- Use the logging module (not print statements)
- Include relevant context in log messages
- Use appropriate log levels:
  - `DEBUG`: Detailed diagnostic information
  - `INFO`: Confirmation that things work as expected
  - `WARNING`: Something unexpected happened
  - `ERROR`: Serious problem, function failed
  - `CRITICAL`: Very serious error

```python
logger = logging.getLogger(__name__)

logger.info("Starting scraper for user: %s", username)
logger.warning("Element not found, retrying...")
logger.error("Failed to connect to portal: %s", error)
```

### Playwright Best Practices

**Architecture:**
- **Browser:** Single browser instance (launch once)
- **BrowserContext:** Isolated environment (like incognito tabs) - create one per test/session
- **Page:** Individual tab within a context - where interactions happen

**Modern Locators (Preferred):**
Use user-facing locators instead of CSS selectors or XPath:
```python
page.get_by_role("button", name="Login")
page.get_by_label("Usuário")
page.get_by_placeholder("Digite sua senha")
page.get_by_text("Bem-vindo")
page.get_by_test_id("submit-button")

# Filter by visibility
page.get_by_role("listitem").filter(visible=True).click()
```

**Web-First Assertions:**
Playwright has built-in auto-waiting. Use `expect` instead of manual waits:
```python
from playwright.sync_api import expect

expect(page.get_by_role("heading")).to_be_visible()
expect(page.get_by_role("button")).to_have_text("Salvar")
```

**General Rules:**
- NEVER use `time.sleep()` - rely on auto-waiting
- Set appropriate timeouts (30s for page loads, 10s for elements)
- Close pages, contexts, and browsers properly
- Use headless mode for production
- Save authentication state with `storage_state` to reuse sessions

```python
# Modern pattern
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(url, wait_until="networkidle")
    
    # Interactions using modern locators
    page.get_by_role("button", name="Login").click()
    
    # Web-first assertions
    expect(page).to_have_url("/dashboard")
    
    # Proper cleanup
    context.close()
    browser.close()
```

### HTML Capture for Debugging
- Save fully rendered HTML to `./debug_output/` for debugging and testing
- Use `print()` for output during scraping (not logging)
- Use `headless=False` and `slow_mo` for visible/slower scraping during development
- This feature is temporary and will be removed in production

```python
import os
import re
from playwright.sync_api import Page

INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')

def _sanitize_filename(title: str) -> str:
    """Remove invalid chars from title for valid filename."""
    filename = INVALID_CHARS.sub("", title)
    filename = filename.replace(" ", "_")
    return filename[:100] or "untitled"

def save_page_html(page: Page, url: str, output_dir: str = "./debug_output") -> str:
    """Navigate to URL and save fully rendered HTML to file."""
    print(f"Navigating to: {url}")
    page.goto(url, wait_until="networkidle")
    
    title = _sanitize_filename(page.title())
    html_content = page.content()
    
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{title}.html")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"HTML saved to: {filepath}")
    return filepath


# Browser configuration for debugging
def get_browser_config():
    return {
        "headless": False,  # Visible browser for debugging
        "slow_mo": 500,     # Slow down interactions by 500ms
    }
```

### Security
- Never hardcode credentials in source code
- Use environment variables for sensitive data
- Add `.env` to `.gitignore`
- Don't log sensitive information

### File Structure
```
/root/projects/python_vivo/
├── src/
│   ├── __init__.py
│   ├── scraper.py          # Main scraping logic
│   ├── database.py         # Database operations
│   ├── models.py           # Data models
│   ├── login.py            # Login handling
│   └── config.py           # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   └── test_database.py
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
└── AGENTS.md
```

### Testing Guidelines
- Write tests for all public functions
- Use descriptive test names: `test_<function>_<scenario>`
- Mock external dependencies (Playwright, network calls)
- Use fixtures for common test setup
- Test both success and error cases

```python
def test_login_success(mock_page):
    """Test successful login flow."""
    result = login(mock_page, "valid_user", "valid_pass")
    assert result is True
    mock_page.goto.assert_called_once()

def test_login_invalid_credentials(mock_page):
    """Test login with invalid credentials."""
    with pytest.raises(LoginError):
        login(mock_page, "user", "wrong_pass")
```

## Database Schema

### Table: geral
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| user | TEXT | Username |
| nome_grupo | TEXT | Group name |
| cota_grupo | REAL | Total group quota |
| nao_atribuida | REAL | Unassigned quota |
| cota_atribuida | REAL | Assigned quota |
| uso_dados | REAL | Data usage |
| porcentagem | REAL | Usage percentage |

### Table: filial
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| filial | TEXT | Branch name |
| codigo | TEXT | Code |
| telefone | TEXT | Phone number |
| grupo | TEXT | Group |

### Table: historico_uso
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| filial_id | INTEGER | Foreign key to filial |
| uso_dados | REAL | Data usage |
| porcentagem | REAL | Usage percentage |
| data_coleta | DATETIME | Collection timestamp |

## Environment Variables
```
VIVO_USERNAME=your_username
VIVO_PASSWORD=your_password
DATABASE_PATH=vivo_gestao.db
LOG_LEVEL=INFO
```

## Common Tasks

### Running the scraper
```bash
uv run python main.py
```

### Creating database tables
```bash
uv run python -c "from src.database import init_db; init_db()"
```

### Resetting database (monthly)
```bash
uv run python -c "from src.database import reset_db; reset_db()"
```
