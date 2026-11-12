# Rentory — SOEN 387 Milestone 2

Rentory is a rental-booking API developed for SOEN 387: Web-Based Enterprise Application Design.

The service uses a published OpenAPI 3.1 contract, separate interface/domain/data layers, JWT authentication and authorization, and concurrency-safe PostgreSQL reservations.

## Project Information

- **Product:** Rentory
- **Course:** SOEN 387 — Fall 2026
- **Milestone:** 2 — November 12, 2026
- **Technology:** Python, FastAPI, PostgreSQL, JWT (RS256)
- **API specification:** OpenAPI 3.1.0

## Contract-First Development

Rentory uses a contract-first workflow for ongoing API development.

The version-controlled `openapi.json` file is the authoritative API contract. It defines the available operations, request and response structures, authentication requirements, and documented HTTP error responses.

### Development Workflow

1. **Define the contract:** Specify new endpoints or changes in `openapi.json` before implementing them.
2. **Validate the contract:** Check that the specification conforms to OpenAPI 3.x.
3. **Implement the service:** Develop the interface, domain/service, and data-source layers according to the contract.
4. **Test conformance:** Verify that the running implementation follows the published contract.
5. **Commit changes:** Track contract, implementation, and test changes in Git.

### Contract Validation

Run from the project directory:

```powershell
python -c "import json; from openapi_spec_validator import validate; validate(json.load(open('openapi.json', encoding='utf-8'))); print('OpenAPI validation passed')"
```

Expected output:

```text
OpenAPI validation passed
```

### Contract Conformance

The conformance tests verify that the running API returns the documented HTTP statuses and JSON response structures.

```powershell
python -m pytest -c NUL tests/conformance_test.py -v
```

The tests cover:

- Health endpoint
- Inventory listing
- Authentication
- Authenticated reservation listing
- Missing authentication token
- Invalid authentication token
- Insufficient permissions
- Reservation creation
- Reservation conflicts

**Current result:** 9 conformance tests passed.

### Contract Source of Truth

The repository's `openapi.json` is the published API specification.

FastAPI also generates an OpenAPI document at `/openapi.json`, but this automatically generated document must not overwrite the version-controlled contract.

New API functionality must be specified in the published contract before implementation.

### Development History

The initial Rentory implementation was developed using FastAPI, and the first OpenAPI specification was generated from the application.

The specification was subsequently reviewed, corrected, independently validated, and established as the authoritative contract.

Further API development follows the contract-first workflow described above.

## Setup (PowerShell)

### 1. Create the PostgreSQL Database

Create an empty PostgreSQL database named `rentory_db`.

Using PostgreSQL's `psql` terminal:

```sql
CREATE DATABASE rentory_db;
```

### 2. Install Dependencies

From the Rentory project directory:

```powershell
python -m pip install -r requirements.txt
```

Create your local environment configuration:

```powershell
Copy-Item .env.example .env
```

### 3. Configure Environment Variables

Open `.env` and replace `YOUR_PASSWORD` with your local PostgreSQL password.

Do not commit `.env` or any private keys to GitHub.

### 4. Initialize the Application

Generate RSA signing keys:

```powershell
python generate_keys.py
```

Create the database tables and demo records:

```powershell
python init_db.py
```

### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

The API runs at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs

FastAPI-generated OpenAPI document:

http://127.0.0.1:8000/openapi.json

**Note:** The authoritative project contract is the `openapi.json` file committed to the repository.

## Demo Accounts (Local Testing Only)

The database initialization script creates two demo accounts.

| Account | Email               | Password       | Permissions                 |
| ------- | ------------------- | -------------- | --------------------------- |
| Booker  | booker@rentory.test | DemoBooker123! | Read and write reservations |
| Reader  | reader@rentory.test | DemoReader123! | Read reservations only      |

These credentials are intentionally insecure and provided only for local demonstration.

Do not expose this service publicly without further security hardening.

## API Endpoints

| Method | Path               | Purpose                                        |
| ------ | ------------------ | ---------------------------------------------- |
| GET    | `/health`          | Database health check                          |
| POST   | `/auth/login`      | Issue a 15-minute RS256 JWT                    |
| GET    | `/items`           | List available inventory                       |
| POST   | `/reservations`    | Create a concurrency-safe reservation          |
| GET    | `/reservations/me` | Retrieve the authenticated user's reservations |

### Authentication

Rentory uses signed JSON Web Tokens (JWT) with RS256.

Users authenticate through `POST /auth/login` and receive an access token.

Protected endpoints require an authorization header containing a bearer token.

The service checks the token's validity and the permissions associated with the authenticated user.

### Authorization

Rentory supports two reservation permissions:

- `reservations:read` — permits reading the authenticated user's reservations.
- `reservations:write` — permits creating reservations.

A user without the required permission cannot perform the protected operation.

### Booking Request

`POST /reservations` requires a bearer token with the `reservations:write` permission.

The request body contains:

```json
{
  "item_id": 1,
  "start_date": "2030-01-10",
  "end_date": "2030-01-12"
}
```

Rental intervals use the convention:

`[start_date, end_date)`

The start date is included, while the end date is excluded.

This allows two reservations to be adjacent without overlapping.

### HTTP Responses

| Status | Meaning                                 |
| ------ | --------------------------------------- |
| 200    | Successful request                      |
| 201    | Reservation successfully created        |
| 401    | Missing or invalid authentication token |
| 403    | Insufficient permissions                |
| 409    | Reservation conflict                    |
| 422    | Invalid request data                    |

These responses are documented in the published OpenAPI contract where applicable.

## Architecture

Rentory separates HTTP handling, business rules, and database operations.

### Interface Layer

**`app/main.py`**

- Defines HTTP endpoints.
- Accepts and validates incoming requests.
- Uses authentication dependencies.
- Converts service results into HTTP responses.

### Authentication

**`app/auth.py`**

- Issues RS256 JWT access tokens.
- Verifies token signatures and validity.
- Checks required permissions.
- Keeps private signing keys on the server.

### Domain Layer

**`app/domain.py`**

- Defines rental date rules.
- Handles domain-specific validation.
- Does not depend on HTTP or database operations.

### Service Layer

**`app/service.py`**

- Coordinates reservation operations.
- Applies domain rules.
- Enforces booking availability.
- Coordinates concurrency-safe transactions.

### Data-Source Layer

**`app/repository.py`**

- Executes PostgreSQL queries.
- Retrieves items and reservations.
- Performs database operations.

**`app/database.py`**

- Manages PostgreSQL connections.

### Database Schema

**`sql/001_initial.sql`**

Defines the initial database structure.

## Concurrency Protection

The contended resource in Rentory is a rental item.

Without concurrency protection, two requests could simultaneously observe an item as available and both create overlapping reservations.

### Strategy: Pessimistic Locking

Rentory uses PostgreSQL row-level locking:

```sql
SELECT ... FOR UPDATE
```

The service locks the relevant item row inside a database transaction before checking reservation availability.

### How It Prevents Double-Booking

1. Two requests attempt to reserve the same item for overlapping dates.
2. The first request obtains the database row lock.
3. The second request waits for the lock.
4. The first request checks availability and creates its reservation.
5. The first transaction commits and releases the lock.
6. The second request acquires the lock and checks availability again.
7. The second request detects the conflict and receives HTTP 409.

This prevents two competing requests from successfully booking the same item for overlapping dates.

## Testing

Keep the FastAPI server running in one terminal.

Run the following commands from a second terminal.

### Authentication Tests

```powershell
python -m pytest -c NUL tests/test_auth.py -v
```

Tests include:

- Missing authentication token
- Invalid authentication token
- Insufficient permissions
- Authorized access

### Concurrency Tests

```powershell
python -m pytest -c NUL tests/test_concurrency.py -v -s
```

The concurrency test sends 10 simultaneous reservation requests for the same item and overlapping dates.

Expected results:

- 1 successful reservation — HTTP 201
- 9 rejected reservations — HTTP 409

This demonstrates that Rentory prevents double-booking under concurrent requests.

### OpenAPI Conformance Tests

```powershell
python -m pytest -c NUL tests/conformance_test.py -v -s
```

These tests validate requests and responses against the published `openapi.json` contract.

Current result: **9 passed**.

### Run All Tests

```powershell
python -m pytest -c NUL tests/ -v -s
```

The `-c NUL` option prevents pytest from loading an unrelated parent-directory configuration file on Windows.

## Milestone 2 Demonstration

The November 12 milestone demonstrates:

1. A running API following its published OpenAPI contract.
2. Separate interface, domain/service, and data-source layers.
3. PostgreSQL persistence.
4. Working JWT authentication and authorization.
5. Successful reservation creation.
6. Concurrency protection preventing double-booking.
7. Passing contract conformance and concurrency tests.

## Project Scope

This repository represents the Milestone 2 implementation of Rentory, not the complete final product.

The current milestone focuses on the published API contract, layered architecture, database persistence, concurrency protection, and authentication.

Additional project-wide requirements, including idempotent operations, foreign-service integration, failure handling, and deployment improvements, are planned for later development.

The service is intended for local development and demonstration.

Before public deployment, additional security measures would be necessary, including TLS, key rotation, rate limiting, and production secret management.
