import os
import turso_serverless
from dotenv import load_dotenv

load_dotenv()

client =turso_serverless.connect(
    os.getenv("DB_URL"),
    auth_token=os.getenv("DB_AUTH_TOKEN"),
)

def _init_db() -> None:
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

