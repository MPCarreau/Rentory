CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    scopes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reservations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    item_id BIGINT NOT NULL REFERENCES items(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    CHECK (end_date > start_date),
    CHECK (status IN ('confirmed', 'cancelled'))
);
CREATE INDEX IF NOT EXISTS idx_reservation_overlap
    ON reservations (item_id, start_date, end_date) WHERE status = 'confirmed';
