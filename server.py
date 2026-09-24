"""
Expense Tracker MCP Server
============================
A FastMCP server that manages personal expenses using SQLite storage.

Tools:
  - add_expense         — Record a new expense
  - list_expenses       — List recent expenses with pagination
  - search_expenses     — Search by keyword and/or category
  - get_expense_summary_month  — Monthly spending summary with category breakdown
  - get_budget_status_of_category — Total spending for a specific category

Transport: stdio (default for Claude Desktop integration)
Reference: https://gofastmcp.com/getting-started/installation
"""
import json
import logging
import sqlite3
from datetime import date, datetime

from fastmcp import FastMCP

from db import client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Many hosting platforms deploy the app code to a read-only directory and
# only give write access to a specific scratch/data path. Allow overriding
# where the DB lives via an env var, and default to a writable temp dir
# rather than assuming the app directory itself is writable.


# Logging goes to stderr so it doesn't corrupt the stdio JSON-RPC stream
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("expense-tracker")

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Expense Tracker",
    instructions=(
        "An expense tracking server. Use the tools to add, list, search, "
        "and summarize expenses. Expenses are stored in a local SQLite database. "
        "All amounts are in INR (₹)."
    ),
)

# NOTE: We intentionally do NOT strip the "subscriptions/listen" handler here.
# A previous version of this file popped it off _lowlevel_server._request_handlers
# as a workaround for modelcontextprotocol/python-sdk#3493 (held-open listen
# streams pinning serverless invocations to the platform timeout on hosts like
# AWS Lambda). That workaround breaks modern (2026-07-28 protocol) clients such
# as Antigravity, which open a subscriptions/listen stream before calling
# tools/list and hard-fail the whole connection ("session not found") if no
# handler is registered — unlike clients that treat a failed auto-open as a
# soft error. Since this server's tool set is static and never publishes a
# change notification, leaving the handler in place costs nothing on a normal
# long-running host (e.g. FastMCP Cloud) and restores compatibility with
# Antigravity and other modern-protocol clients.

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_inr(amount: float) -> str:
    """Format an amount as INR currency."""
    return f"₹{amount:,.2f}"


def _normalize_category(category: str | None) -> str:
    """Normalize category to lowercase, stripped, defaulting to 'uncategorized'."""
    if not category or not category.strip():
        return "uncategorized"
    return category.strip().lower()


def _validate_date(date_str: str | None) -> str:
    """Validate and return a date string in YYYY-MM-DD format.
    Returns today's date if None is provided.
    """
    if not date_str:
        return date.today().isoformat()
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
def add_expense(
    amount: float,
    description: str,
    category: str | None = None,
    date: str | None = None,
) -> str:
    """Add a new expense record.

    Args:
        amount: The expense amount in INR (must be greater than 0).
        description: What the expense was for.
        category: Optional category (e.g. 'food', 'groceries', 'transport').
                  Defaults to 'uncategorized'.
        date: Optional date in YYYY-MM-DD format. Defaults to today.

    Returns:
        A confirmation message with the new expense details.
    """
    # Validate amount
    if amount <= 0:
        return json.dumps({"error": "Amount must be greater than 0"})

    if not description or not description.strip():
        return json.dumps({"error": "Description must not be empty"})

    normalized_category = _normalize_category(category)

    try:
        validated_date = _validate_date(date)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    conn = client
    try:
        cursor = conn.execute(
            """
            INSERT INTO expenses (amount, description, category, date)
            VALUES (?, ?, ?, ?)
            """,
            (amount, description.strip(), normalized_category, validated_date),
        )
        conn.commit()
        expense_id = cursor.lastrowid
        logger.info(
            "Added expense #%d: %s %s (%s) on %s",
            expense_id,
            _format_inr(amount),
            description,
            normalized_category,
            validated_date,
        )
        return json.dumps(
            {
                "status": "created",
                "id": expense_id,
                "amount": _format_inr(amount),
                "description": description.strip(),
                "category": normalized_category,
                "date": validated_date,
            },
            indent=2,
        )
    finally:
        conn.close()


@mcp.tool
def list_expenses(limit: int = 20, offset: int = 0) -> str:
    """List recent expenses ordered by date (newest first).

    Args:
        limit: Maximum number of expenses to return (default 20, max 100).
        offset: Number of expenses to skip for pagination (default 0).

    Returns:
        A JSON list of expenses with total count.
    """
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    conn = client
    try:
        # Get total count
        total = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

        # Get paginated results
        rows = conn.execute(
            """
            SELECT id, amount, description, category, date, created_at
            FROM expenses
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        expenses = []
        for row in rows:
            expense = _row_to_dict(row)
            expense["amount_formatted"] = _format_inr(expense["amount"])
            expenses.append(expense)

        return json.dumps(
            {
                "expenses": expenses,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total,
            },
            indent=2,
        )
    finally:
        conn.close()


@mcp.tool
def search_expenses(keyword: str | None = None, category: str | None = None) -> str:
    """Search expenses by keyword in description and/or by category.

    At least one of keyword or category must be provided.

    Args:
        keyword: Optional text to search for in expense descriptions
                 (case-insensitive).
        category: Optional category to filter by (e.g. 'food', 'groceries').

    Returns:
        A JSON list of matching expenses.
    """
    if not keyword and not category:
        return json.dumps(
            {"error": "At least one of 'keyword' or 'category' must be provided"}
        )

    conditions = []
    params = []

    if keyword and keyword.strip():
        conditions.append("description LIKE ?")
        params.append(f"%{keyword.strip()}%")

    if category and category.strip():
        normalized = _normalize_category(category)
        conditions.append("category = ?")
        params.append(normalized)

    where_clause = " AND ".join(conditions)

    conn = client
    try:
        rows = conn.execute(
            f"""
            SELECT id, amount, description, category, date, created_at
            FROM expenses
            WHERE {where_clause}
            ORDER BY date DESC, id DESC
            """,
            params,
        ).fetchall()

        expenses = []
        for row in rows:
            expense = _row_to_dict(row)
            expense["amount_formatted"] = _format_inr(expense["amount"])
            expenses.append(expense)

        return json.dumps(
            {
                "keyword": keyword,
                "category": category,
                "matches": expenses,
                "count": len(expenses),
            },
            indent=2,
        )
    finally:
        conn.close()


@mcp.tool
def get_expense_summary_month(month: int | None = None, year: int | None = None) -> str:
    """Get a spending summary for a specific month.

    Args:
        month: Month number (1-12). Defaults to the current month.
        year: Year (e.g. 2025). Defaults to the current year.

    Returns:
        A JSON summary with total spend, expense count, and
        per-category breakdown.
    """
    today = date.today()
    month = month or today.month
    year = year or today.year

    if not (1 <= month <= 12):
        return json.dumps({"error": "Month must be between 1 and 12"})
    if year < 2000 or year > 2100:
        return json.dumps({"error": "Year must be between 2000 and 2100"})

    # Build date range for the month
    date_start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        date_end = f"{year + 1:04d}-01-01"
    else:
        date_end = f"{year:04d}-{month + 1:02d}-01"

    conn = client
    try:
        # Overall totals
        summary_row = conn.execute(
            """
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
            FROM expenses
            WHERE date >= ? AND date < ?
            """,
            (date_start, date_end),
        ).fetchone()

        total_count = summary_row["count"]
        total_amount = summary_row["total"]

        # Category breakdown
        category_rows = conn.execute(
            """
            SELECT category,
                   COUNT(*) as count,
                   SUM(amount) as total
            FROM expenses
            WHERE date >= ? AND date < ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (date_start, date_end),
        ).fetchall()

        categories = []
        for row in category_rows:
            categories.append(
                {
                    "category": row["category"],
                    "count": row["count"],
                    "total": row["total"],
                    "total_formatted": _format_inr(row["total"]),
                    "percentage": round(
                        (row["total"] / total_amount * 100) if total_amount > 0 else 0,
                        1,
                    ),
                }
            )

        month_name = datetime(year, month, 1).strftime("%B %Y")

        return json.dumps(
            {
                "month": month_name,
                "total_expenses": total_count,
                "total_amount": total_amount,
                "total_formatted": _format_inr(total_amount),
                "average_per_expense": _format_inr(
                    total_amount / total_count if total_count > 0 else 0
                ),
                "category_breakdown": categories,
            },
            indent=2,
        )
    finally:
        conn.close()


@mcp.tool
def get_budget_status_of_category(
    category: str,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """Get total spending for a specific category, optionally filtered by month.

    Args:
        category: The expense category to check (e.g. 'food', 'groceries',
                  'transport').
        month: Optional month number (1-12). Defaults to current month.
        year: Optional year (e.g. 2025). Defaults to current year.

    Returns:
        A JSON summary with total spent, number of transactions,
        and average per transaction for the given category.
    """
    if not category or not category.strip():
        return json.dumps({"error": "Category must not be empty"})

    normalized = _normalize_category(category)
    today = date.today()
    month = month or today.month
    year = year or today.year

    if not (1 <= month <= 12):
        return json.dumps({"error": "Month must be between 1 and 12"})

    # Build date range
    date_start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        date_end = f"{year + 1:04d}-01-01"
    else:
        date_end = f"{year:04d}-{month + 1:02d}-01"

    conn = client
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) as count,
                   COALESCE(SUM(amount), 0) as total,
                   COALESCE(AVG(amount), 0) as average,
                   MIN(amount) as min_expense,
                   MAX(amount) as max_expense
            FROM expenses
            WHERE category = ? AND date >= ? AND date < ?
            """,
            (normalized, date_start, date_end),
        ).fetchone()

        month_name = datetime(year, month, 1).strftime("%B %Y")

        # Get recent transactions in this category
        recent = conn.execute(
            """
            SELECT id, amount, description, date
            FROM expenses
            WHERE category = ? AND date >= ? AND date < ?
            ORDER BY date DESC
            LIMIT 5
            """,
            (normalized, date_start, date_end),
        ).fetchall()

        recent_list = []
        for r in recent:
            recent_list.append(
                {
                    "id": r["id"],
                    "amount": _format_inr(r["amount"]),
                    "description": r["description"],
                    "date": r["date"],
                }
            )

        return json.dumps(
            {
                "category": normalized,
                "month": month_name,
                "total_spent": row["total"],
                "total_formatted": _format_inr(row["total"]),
                "transaction_count": row["count"],
                "average_per_transaction": _format_inr(row["average"]),
                "min_expense": _format_inr(row["min_expense"])
                if row["min_expense"]
                else None,
                "max_expense": _format_inr(row["max_expense"])
                if row["max_expense"]
                else None,
                "recent_transactions": recent_list,
            },
            indent=2,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Expense Tracker MCP server (stdio transport)…")
    mcp.run(transport="http", host="0.0.0.0", port=8000, stateless_http=True)