import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User


SECRET = os.getenv("JWT_SECRET", "development-only-change-this-secret")
if os.getenv("APP_ENV") == "production" and (not os.getenv("JWT_SECRET") or len(SECRET) < 32):
    raise RuntimeError("JWT_SECRET must be set to at least 32 characters in production")
password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def create_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user_id, "iat": now, "exp": now + timedelta(hours=12)}, SECRET, algorithm="HS256")


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
        user = db.get(User, payload.get("sub"))
    except (jwt.PyJWTError, TypeError):
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user
