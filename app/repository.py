"""Database operations; caller owns transaction and locking order."""


def find_user_by_email(conn, email):
    row = conn.execute(
        "SELECT id, email, password_hash, scopes FROM users WHERE email = %s", (email,)
    ).fetchone()
    return dict(zip(("id", "email", "password_hash", "scopes"), row)) if row else None


def list_items(conn):
    rows = conn.execute("SELECT id, name FROM items ORDER BY id").fetchall()
    return [{"id": r[0], "name": r[1]} for r in rows]


def lock_item(conn, item_id):
    return conn.execute("SELECT id FROM items WHERE id = %s FOR UPDATE", (item_id,)).fetchone()


def conflicting_reservation(conn, item_id, start_date, end_date):
    return conn.execute(
        """SELECT id FROM reservations
           WHERE item_id = %s AND status = 'confirmed'
             AND start_date < %s AND end_date > %s LIMIT 1""",
        (item_id, end_date, start_date),
    ).fetchone() is not None


def create_reservation(conn, user_id, item_id, start_date, end_date):
    row = conn.execute(
        """INSERT INTO reservations (user_id, item_id, start_date, end_date)
           VALUES (%s, %s, %s, %s)
           RETURNING id, user_id, item_id, start_date, end_date, status""",
        (user_id, item_id, start_date, end_date),
    ).fetchone()
    return dict(zip(("id", "user_id", "item_id", "start_date", "end_date", "status"), row))


def user_reservations(conn, user_id):
    rows = conn.execute(
        """SELECT id, user_id, item_id, start_date, end_date, status
           FROM reservations WHERE user_id = %s ORDER BY id""", (user_id,)
    ).fetchall()
    fields = ("id", "user_id", "item_id", "start_date", "end_date", "status")
    return [dict(zip(fields, r)) for r in rows]
