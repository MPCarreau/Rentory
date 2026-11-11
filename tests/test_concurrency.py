
"""Live-server concurrency test: 10 competing bookings; exactly one wins."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import requests

BASE = "http://127.0.0.1:8000"


def test_concurrent_reservations():
    # Authenticate as a user allowed to create reservations.
    login = requests.post(
        f"{BASE}/auth/login",
        json={
            "email": "booker@rentory.test",
            "password": "DemoBooker123!"
        },
        timeout=10
    )
    login.raise_for_status()

    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Use a different future date range for each test run.
    offset = uuid.uuid4().int % 100000
    start = date(2030, 1, 1) + timedelta(days=offset)

    body = {
        "item_id": 1,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=2)).isoformat()
    }

    # Send 10 concurrent requests for the same item and dates.
    def attempt(_):
        response = requests.post(
            f"{BASE}/reservations",
            json=body,
            headers=headers,
            timeout=30
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, range(10)))

    successes = sum(
        code == 201 for code, _ in results
    )

    conflicts = sum(
        code == 409 and payload.get("detail") == "item_unavailable"
        for code, payload in results
    )

    print(
        f"\nConcurrent requests: 10 | "
        f"Successful: {successes} | Conflicts: {conflicts}"
    )

    assert successes == 1, f"Expected 1 successful reservation: {results}"
    assert conflicts == 9, f"Expected 9 conflicts: {results}"

    print("PASS: No double booking")
