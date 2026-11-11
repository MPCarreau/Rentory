"""Create tables and demo users; safe to rerun without deleting reservations."""
import bcrypt
from pathlib import Path
from app.database import connect

with connect() as conn:
    conn.execute(Path("sql/001_initial.sql").read_text(encoding="utf-8"))
    for email, password, scopes in [
        ("booker@rentory.test", "DemoBooker123!", "reservations:read reservations:write"),
        ("reader@rentory.test", "DemoReader123!", "reservations:read"),
    ]:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            """INSERT INTO users (email, password_hash, scopes)
               VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING""",
            (email, password_hash, scopes),
        )
    conn.execute("INSERT INTO items (id, name) VALUES (1, 'Camera kit') ON CONFLICT (id) DO NOTHING")
print("Database initialized. Demo accounts are listed in README.md")
