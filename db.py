import os
import turso_serverless
from dotenv import load_dotenv

load_dotenv()


def get_client():
    db_url = os.getenv("DB_URL")
    db_auth_token = os.getenv("DB_AUTH_TOKEN")

    if not db_url:
        raise RuntimeError("DB_URL environment variable is not configured")

    if not db_auth_token:
        raise RuntimeError("DB_AUTH_TOKEN environment variable is not configured")

    return turso_serverless.connect(
        db_url,
        auth_token=db_auth_token,
    )

def _init_db() -> None:
    client = get_client()
    client.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'uncategorized',
            date DATE NOT NULL,
            created_at DATE NOT NULL DEFAULT (date('now'))
        )
    """)
    client.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses (date)")
    client.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category)")

