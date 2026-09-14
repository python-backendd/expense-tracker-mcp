# Expense Tracker MCP Server

A minimal expense tracking server built with [FastMCP](https://gofastmcp.com) and SQLite.

## Setup

```bash
# Install dependencies (from the mcp_demo root)
pip install fastmcp
```

## Running the Server

```bash
# From the mcp_demo root
python -m expense_tracker.server
```

Or run directly:

```bash
cd expense_tracker
python server.py
```

## MCP Inspector (Development)

Use the FastMCP Inspector to interactively test and debug tools in the browser:

```bash
cd expense_tracker
fastmcp dev inspector server.py
```

## Tools

### `add_expense`
Record a new expense.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | float | ✅ | Amount in INR (must be > 0) |
| `description` | string | ✅ | What the expense was for |
| `category` | string | ❌ | Category (e.g. "food", "groceries"). Defaults to "uncategorized" |
| `date` | string | ❌ | Date in YYYY-MM-DD format. Defaults to today |

### `list_expenses`
List recent expenses with pagination.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | ❌ | Max results (default 20, max 100) |
| `offset` | int | ❌ | Skip N results for pagination |

### `search_expenses`
Search by keyword and/or category. At least one must be provided.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | ❌ | Search in descriptions (case-insensitive) |
| `category` | string | ❌ | Filter by category |

### `get_expense_summary_month`
Get monthly spending summary with category breakdown.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `month` | int | ❌ | Month (1-12). Defaults to current month |
| `year` | int | ❌ | Year. Defaults to current year |

### `get_budget_status_of_category`
Get total spending for a specific category.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | ✅ | Category to check (e.g. "food") |
| `month` | int | ❌ | Month (1-12). Defaults to current month |
| `year` | int | ❌ | Year. Defaults to current year |

## Database

The SQLite database (`expenses.db`) is created automatically in the `expense_tracker/` directory on first run.

### Schema

```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'uncategorized',
    date DATE NOT NULL,
    created_at DATE NOT NULL DEFAULT (date('now'))
);
```

## Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "python",
      "args": ["-m", "expense_tracker.server"],
      "cwd": "/path/to/mcp_demo"
    }
  }
}
```
