
"""
Rentory - OpenAPI Contract Conformance Tests

These tests send real HTTP requests to the running FastAPI server
and verify that requests and responses match openapi.json.

Coverage:
- Health endpoint
- Item listing
- Authentication
- Authenticated reservation listing
- Missing and invalid tokens
- Insufficient permissions
- Reservation creation
- Double-booking conflicts
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path

import requests
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

# Address of the running Rentory API.
BASE = "http://127.0.0.1:8000"

# Load the OpenAPI contract from the project root.
CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "openapi.json"
)

CONTRACT = json.loads(
    CONTRACT_PATH.read_text(encoding="utf-8")
)


# --------------------------------------------------
# 2. OpenAPI Schema Validation
# --------------------------------------------------

# Register the complete OpenAPI document so references
# such as #/components/schemas/LoginRequest can be resolved.
#
# We explicitly specify JSON Schema Draft 2020-12 because
# the OpenAPI document itself does not declare $schema.
CONTRACT_URI = "https://rentory.local/openapi.json"

REGISTRY = Registry().with_resource(
    CONTRACT_URI,
    Resource(
        contents=CONTRACT,
        specification=DRAFT202012
    )
)


def validate_schema(schema, data):
    """
    Validate JSON against an OpenAPI schema.

    The schema may contain $ref references to reusable
    definitions in the full OpenAPI contract.
    """

    # Register a wrapper document that contains the schema
    # at a known location inside the OpenAPI document.
    #
    # This avoids treating an isolated $ref as the root
    # document, which caused the previous PointerToNowhere error.
    validation_schema = {
        "$ref": "#/$defs/target",
        "$defs": {
            "target": schema
        },
        "components": CONTRACT.get("components", {})
    }

    validator = Draft202012Validator(
        validation_schema,
        format_checker=FormatChecker()
    )

    validator.validate(data)


def get_operation(path, method):
    """
    Retrieve an endpoint's definition from openapi.json.
    """

    return CONTRACT["paths"][path][method.lower()]


def validate_request(path, method, body):
    """
    Validate a request body against the OpenAPI contract.
    """

    operation = get_operation(path, method)

    request_body = operation.get("requestBody")

    # Some endpoints, such as GET /health, have no body.
    if request_body is None:
        return

    schema = request_body["content"]["application/json"]["schema"]

    validate_schema(schema, body)


def validate_response(path, method, response):
    """
    Verify that:
    1. The HTTP status is documented.
    2. The response JSON matches its documented schema.
    """

    operation = get_operation(path, method)

    status = str(response.status_code)

    documented_responses = operation["responses"]

    # The API must document every tested response status.
    assert status in documented_responses, (
        f"{method.upper()} {path}: HTTP {status} "
        f"is missing from the OpenAPI contract. "
        f"Documented statuses: {list(documented_responses)}"
    )

    response_spec = documented_responses[status]

    content = response_spec.get("content", {})

    # Responses without documented content should have
    # an empty response body.
    if not content:
        assert not response.content
        return

    assert "application/json" in content, (
        f"No JSON response schema for HTTP {status}"
    )

    schema = content["application/json"]["schema"]

    validate_schema(schema, response.json())


# --------------------------------------------------
# 3. Authentication Helper
# --------------------------------------------------

def login(email, password):
    """
    Log in using a demo account.

    Validate the login request and response against
    the OpenAPI contract before returning the token.
    """

    body = {
        "email": email,
        "password": password
    }

    validate_request("/auth/login", "post", body)

    response = requests.post(
        f"{BASE}/auth/login",
        json=body,
        timeout=10
    )

    assert response.status_code == 200, response.text

    validate_response("/auth/login", "post", response)

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# --------------------------------------------------
# 4. Reservation Test Data
# --------------------------------------------------

def unique_dates():
    """
    Generate a unique future date range.

    This prevents previous test reservations from
    interfering with the current test.
    """

    offset = uuid.uuid4().int % 100000

    start = date(2030, 1, 1) + timedelta(days=offset)

    return {
        "item_id": 1,
        "start_date": start.isoformat(),
        "end_date": (
            start + timedelta(days=2)
        ).isoformat()
    }


# --------------------------------------------------
# 5. Public Endpoint Tests
# --------------------------------------------------

def test_health_contract():
    """GET /health must return a valid HTTP 200 response."""

    response = requests.get(
        f"{BASE}/health",
        timeout=10
    )

    assert response.status_code == 200

    validate_response("/health", "get", response)


def test_items_contract():
    """GET /items must return a valid item listing."""

    response = requests.get(
        f"{BASE}/items",
        timeout=10
    )

    assert response.status_code == 200

    validate_response("/items", "get", response)


# --------------------------------------------------
# 6. Authentication Tests
# --------------------------------------------------

def test_login_contract():
    """
    POST /auth/login must accept valid credentials
    and return a valid authentication response.
    """

    login(
        "booker@rentory.test",
        "DemoBooker123!"
    )


def test_reservations_me_contract():
    """
    An authenticated user must be able to retrieve
    their own reservations.
    """

    headers = login(
        "booker@rentory.test",
        "DemoBooker123!"
    )

    response = requests.get(
        f"{BASE}/reservations/me",
        headers=headers,
        timeout=10
    )

    assert response.status_code == 200

    validate_response(
        "/reservations/me",
        "get",
        response
    )


def test_missing_token_contract():
    """
    A protected endpoint must reject requests
    without an authentication token.
    """

    response = requests.get(
        f"{BASE}/reservations/me",
        timeout=10
    )

    assert response.status_code == 401

    validate_response(
        "/reservations/me",
        "get",
        response
    )


def test_invalid_token_contract():
    """
    A protected endpoint must reject an invalid token.
    """

    response = requests.get(
        f"{BASE}/reservations/me",
        headers={
            "Authorization": "Bearer invalid.token.value"
        },
        timeout=10
    )

    assert response.status_code == 401

    validate_response(
        "/reservations/me",
        "get",
        response
    )


def test_insufficient_scope_contract():
    """
    A user with read-only permissions must not
    be allowed to create reservations.
    """

    # The reader account has reservations:read,
    # but not reservations:write.
    headers = login(
        "reader@rentory.test",
        "DemoReader123!"
    )

    body = unique_dates()

    validate_request("/reservations", "post", body)

    response = requests.post(
        f"{BASE}/reservations",
        headers=headers,
        json=body,
        timeout=10
    )

    assert response.status_code == 403

    validate_response(
        "/reservations",
        "post",
        response
    )


# --------------------------------------------------
# 7. Reservation Creation Test
# --------------------------------------------------

def test_create_reservation_contract():
    """
    An authorized user must be able to create
    a reservation for an available item.
    """

    headers = login(
        "booker@rentory.test",
        "DemoBooker123!"
    )

    body = unique_dates()

    validate_request("/reservations", "post", body)

    response = requests.post(
        f"{BASE}/reservations",
        headers=headers,
        json=body,
        timeout=10
    )

    assert response.status_code == 201, response.text

    validate_response(
        "/reservations",
        "post",
        response
    )


# --------------------------------------------------
# 8. Booking Conflict Test
# --------------------------------------------------

def test_booking_conflict_contract():
    """
    A rental item must not be double-booked.

    The first reservation should succeed.
    A second reservation for the same item and
    overlapping dates must return HTTP 409.
    """

    headers = login(
        "booker@rentory.test",
        "DemoBooker123!"
    )

    body = unique_dates()

    validate_request("/reservations", "post", body)

    # First booking should succeed.
    first = requests.post(
        f"{BASE}/reservations",
        headers=headers,
        json=body,
        timeout=10
    )

    assert first.status_code == 201, first.text

    validate_response(
        "/reservations",
        "post",
        first
    )

    # Second booking overlaps the first.
    second = requests.post(
        f"{BASE}/reservations",
        headers=headers,
        json=body,
        timeout=10
    )

    assert second.status_code == 409, second.text

    validate_response(
        "/reservations",
        "post",
        second
    )
