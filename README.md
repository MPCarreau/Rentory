# Rentory — SOEN 387 Milestone 2

Minimal rental-booking API with a published OpenAPI contract, separate domain/data layers, JWT authentication, and concurrency-safe PostgreSQL reservations.

## Setup (PowerShell)

1. Create an empty PostgreSQL database named `rentory_db` (e.g. `CREATE DATABASE rentory_db;` in psql).
2. From this project directory, run:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Edit `.env` and replace `YOUR_PASSWORD` with your local PostgreSQL password. Do not commit `.env`.
4. Generate signing keys and create tables/demo records:

```powershell
python generate_keys.py
python init_db.py
```

5. Start the API:

```powershell
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` (interactive API contract) or `http://127.0.0.1:8000/openapi.json` (machine-readable OpenAPI).

## Demo accounts (local testing only)

- Booker: `booker@rentory.test` / `DemoBooker123!` (read + write reservations)
- Reader: `reader@rentory.test` / `DemoReader123!` (read only)

These are intentionally insecure sample credentials for local demonstration. Replace before deployment. Do not expose this service publicly without further hardening.

## Routes

| Method | Path               | Purpose                                 |
| ------ | ------------------ | --------------------------------------- |
| GET    | `/health`          | DB health                               |
| POST   | `/auth/login`      | Issue 15-minute RS256 JWT               |
| GET    | `/items`           | List inventory                          |
| POST   | `/reservations`    | Authenticated, concurrency-safe booking |
| GET    | `/reservations/me` | Authenticated user's bookings           |

### Booking request

`POST /reservations` requires a Bearer token with `reservations:write` and JSON containing `item_id`, `start_date`, `end_date` (ISO dates). Rental intervals are `[start_date, end_date)`, so adjacent reservations are allowed.

## Tests and demo

Keep the server running in another terminal, then:

```powershell
python tests/test_auth.py
python tests/test_concurrency.py
```

Authentication demonstrates 401 for missing/invalid tokens, 403 for insufficient scope, and 200 for an authorized reader. Concurrency sends 10 simultaneous overlapping requests for item 1 using a fresh date range. Expected: **1 x 201**, **9 x 409**.

## Architecture and concurrency

- `app/main.py`: HTTP endpoints, input validation, authentication dependencies.
- `app/auth.py`: RS256 JWT issuance/verification, scopes; private key stays server-side.
- `app/domain.py`: pure rental date rules; no HTTP or database imports.
- `app/service.py`: booking use case; enforces domain rule and lock-before-check.
- `app/repository.py`: SQL data access.
- `app/database.py`: PostgreSQL connection.
- `sql/001_initial.sql`: schema.

**Race prevented:** Two requests could both read an item as free and insert overlapping reservations. `SELECT ... FOR UPDATE` serializes competing bookings on the same item row inside a transaction; after the first commits, the second rechecks and returns 409. The transaction commits only after insertion.

## Scope

This is a **Milestone 2 prototype**, not the full Rentory product. It intentionally omits registration, dashboard, cancellation, payments, email, and delegation. JWT authentication is local to the service for demo purposes; TLS, key rotation, rate limiting, account recovery, and production secret management would be needed before public deployment.
