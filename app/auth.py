import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

load_dotenv()
bearer = HTTPBearer(auto_error=False)


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def issue_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user["id"]),
        "scope": user["scopes"],
        "iss": os.getenv("JWT_ISSUER", "rentory-local"),
        "aud": os.getenv("JWT_AUDIENCE", "rentory-api"),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=int(os.getenv("TOKEN_MINUTES", "15"))),
    }
    private_key = Path(os.getenv("JWT_PRIVATE_KEY_FILE", "keys/private.pem")).read_text()
    return jwt.encode(claims, private_key, algorithm="RS256")


def current_user(
    security_scopes: SecurityScopes,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing_token", headers={"WWW-Authenticate": "Bearer"})
    try:
        public_key = Path(os.getenv("JWT_PUBLIC_KEY_FILE", "keys/public.pem")).read_text()
        payload = jwt.decode(
            credentials.credentials,
            public_key,
            algorithms=["RS256"],
            issuer=os.getenv("JWT_ISSUER", "rentory-local"),
            audience=os.getenv("JWT_AUDIENCE", "rentory-api"),
            options={"require": ["sub", "iss", "aud", "exp", "iat", "nbf"]},
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, OSError):
        raise HTTPException(status_code=401, detail="invalid_token", headers={"WWW-Authenticate": "Bearer"})
    granted = set(payload.get("scope", "").split())
    if not set(security_scopes.scopes).issubset(granted):
        raise HTTPException(status_code=403, detail="insufficient_scope")
    return {"id": user_id, "scopes": granted}
