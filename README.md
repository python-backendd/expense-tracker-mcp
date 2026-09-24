# Expense Tracker MCP Server

A minimal expense tracking server built with [FastMCP](https://gofastmcp.com) and [Turso](https://turso.tech) (a SQLite-compatible cloud database).

## Setup

```bash
# Install dependencies (from the mcp_demo root)
pip install fastmcp turso_serverless python-dotenv
```

### Environment variables

Create a `.env` file in `expense_tracker/` with your Turso database credentials:

```bash
DB_URL=libsql://your-db-name-yourusername.turso.io
DB_AUTH_TOKEN=your-auth-token-here
```

Get these from the Turso CLI:

```bash
turso db show your-db-name --url
turso db tokens create your-db-name
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

Expenses are stored in a [Turso](https://turso.tech) cloud database (SQLite-compatible), connected via the `turso_serverless` DB-API 2.0 driver over HTTP. The connection is configured through the `DB_URL` and `DB_AUTH_TOKEN` environment variables — see [Setup](#setup) above. The `expenses` table and its indexes are created automatically on first run if they don't already exist.

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
      "command": "/Users/krishnasinghal/Projects/mcp_demo/.venv/bin/fastmcp",
      "args": ["run", "/Users/krishnasinghal/Projects/mcp_demo/expense_tracker/server.py:mcp"],
      "env": {
        "DB_URL": "libsql://your-db-name-yourusername.turso.io",
        "DB_AUTH_TOKEN": "your-auth-token-here"
      }
    }
  }
}
```