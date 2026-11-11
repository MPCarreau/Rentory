
"""Live-server authentication tests: 401, 403, and 200."""

import requests

BASE = "http://127.0.0.1:8000"


def test_authentication():
    # Test 1: Missing token should return 401.
    missing = requests.get(
        f"{BASE}/reservations/me",
        timeout=10
    )
    assert missing.status_code == 401, missing.text

    # Test 2: Log in with a read-only account.
    reader = requests.post(
        f"{BASE}/auth/login",
        json={
            "email": "reader@rentory.test",
            "password": "DemoReader123!"
        },
        timeout=10
    )
    assert reader.status_code == 200, reader.text

    reader_headers = {
        "Authorization": f"Bearer {reader.json()['access_token']}"
    }

    # Test 3: Reader cannot create reservations (403).
    forbidden = requests.post(
        f"{BASE}/reservations",
        headers=reader_headers,
        json={
            "item_id": 1,
            "start_date": "2030-01-01",
            "end_date": "2030-01-02"
        },
        timeout=10
    )
    assert forbidden.status_code == 403, forbidden.text

    # Test 4: Reader can view their reservations (200).
    allowed = requests.get(
        f"{BASE}/reservations/me",
        headers=reader_headers,
        timeout=10
    )
    assert allowed.status_code == 200, allowed.text

    # Test 5: Invalid JWT should return 401.
    bad = requests.get(
        f"{BASE}/reservations/me",
        headers={
            "Authorization": "Bearer invalid.token.value"
        },
        timeout=10
    )
    assert bad.status_code == 401, bad.text

    print(
        "\nPASS: 401 missing/invalid token; "
        "403 insufficient scope; 200 authorized"
    )
