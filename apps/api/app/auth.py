import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .db import get_db
from .models import User, UserSettings


SECRET = os.getenv("JWT_SECRET", "development-only-change-this-secret")
INFRA_URL = os.getenv("INFRA_URL", "").rstrip("/")
INFRA_APP_ID = os.getenv("INFRA_APP_ID", "")
INFRA_SECRET_KEY = os.getenv("INFRA_SECRET_KEY", "")
HUB_AUTH = bool(INFRA_URL)
if HUB_AUTH and (not INFRA_APP_ID or not INFRA_SECRET_KEY.startswith("sk_")):
    raise RuntimeError("INFRA_APP_ID and INFRA_SECRET_KEY are required with INFRA_URL")
if os.getenv("APP_ENV") == "production" and not HUB_AUTH:
    raise RuntimeError("Production requires App System authentication (INFRA_URL)")
hub_keys = jwt.PyJWKClient(f"{INFRA_URL}/.well-known/jwks.json", cache_jwk_set=True, lifespan=300) if HUB_AUTH else None
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
    if HUB_AUTH:
        try:
            assert hub_keys is not None
            signing_key = hub_keys.get_signing_key_from_jwt(credentials.credentials)
            claims = jwt.decode(
                credentials.credentials,
                signing_key.key,
                algorithms=["ES256"],
                issuer=INFRA_URL,
                audience=INFRA_APP_ID,
                options={"require": ["iss", "sub", "aud", "exp", "iat"]},
            )
            if claims.get("typ") != "access" or not isinstance(claims.get("sub"), str) or claims["sub"].startswith("svc_"):
                raise jwt.InvalidTokenError("wrong token type")
        except jwt.PyJWKClientConnectionError:
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{INFRA_APP_ID}:{claims['sub']}"))
        user = db.get(User, user_id)
        if user:
            return user
        try:
            response = httpx.get(
                f"{INFRA_URL}/api/v1/me",
                headers={"authorization": f"Bearer {INFRA_SECRET_KEY}", "x-infra-access-token": credentials.credentials},
                timeout=5,
            )
            response.raise_for_status()
            profile = response.json().get("data")
        except (httpx.HTTPError, ValueError):
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
        if not isinstance(profile, dict) or not isinstance(profile.get("user"), dict) or profile["user"].get("id") != claims["sub"]:
            raise HTTPException(status_code=401, detail="App System membership required")
        email = profile["user"].get("email") or f"{user_id}@hub.invalid"
        db.add(User(id=user_id, email=email.lower(), password_hash="external:app_system"))
        db.add(UserSettings(user_id=user_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=409, detail="Email is already linked to another finance profile")
        return user

    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
        user = db.get(User, payload.get("sub"))
    except (jwt.PyJWTError, TypeError):
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user
