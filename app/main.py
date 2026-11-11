from datetime import date
from fastapi import FastAPI, HTTPException, Security
from pydantic import BaseModel, Field

from app import auth, repository, service
from app.database import connect

app = FastAPI(title="Rentory", version="0.2.0", description="Milestone 2: authentication and concurrency-safe rental bookings")


class LoginRequest(BaseModel):
    email: str
    password: str


class ReservationRequest(BaseModel):
    item_id: int
    start_date: date
    end_date: date


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    start_date: date
    end_date: date
    status: str


@app.get("/health")
def health():
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/auth/login")
def login(body: LoginRequest):
    with connect() as conn:
        user = repository.find_user_by_email(conn, body.email)
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    return {"access_token": auth.issue_token(user), "token_type": "bearer"}


@app.get("/items")
def items():
    with connect() as conn:
        return repository.list_items(conn)


@app.post("/reservations", status_code=201, response_model=ReservationResponse)
def reserve(body: ReservationRequest, user=Security(auth.current_user, scopes=["reservations:write"])):
    try:
        with connect() as conn:
            return service.reserve(conn, user["id"], body.item_id, body.start_date, body.end_date)
    except service.ItemNotFound:
        raise HTTPException(status_code=404, detail="item_not_found")
    except service.ItemUnavailable:
        raise HTTPException(status_code=409, detail="item_unavailable")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/reservations/me", response_model=list[ReservationResponse])
def my_reservations(user=Security(auth.current_user, scopes=["reservations:read"])):
    with connect() as conn:
        return repository.user_reservations(conn, user["id"])
