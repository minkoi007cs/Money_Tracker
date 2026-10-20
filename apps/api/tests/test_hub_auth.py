from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app import auth, main


def test_app_system_tokens_and_user_isolation(client, monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    class Keys:
        def get_signing_key_from_jwt(self, _token):
            return type("Key", (), {"key": public_key})()

    class Profile:
        def __init__(self, user_id):
            self.user_id = user_id

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"user": {"id": self.user_id, "email": f"{self.user_id}@example.com"}}}

    def profile(_url, headers, timeout):
        claims = jwt.decode(headers["x-infra-access-token"], public_key, algorithms=["ES256"], options={"verify_aud": False})
        return Profile(claims["sub"])

    monkeypatch.setattr(auth, "HUB_AUTH", True)
    monkeypatch.setattr(main, "HUB_AUTH", True)
    monkeypatch.setattr(auth, "INFRA_URL", "https://system.example")
    monkeypatch.setattr(auth, "INFRA_APP_ID", "money-tracker-app")
    monkeypatch.setattr(auth, "INFRA_SECRET_KEY", "sk_test")
    monkeypatch.setattr(auth, "hub_keys", Keys())
    monkeypatch.setattr(auth.httpx, "get", profile)

    def token(subject, audience="money-tracker-app", token_type="access"):
        now = datetime.now(timezone.utc)
        return jwt.encode({"iss": "https://system.example", "sub": subject, "aud": audience, "typ": token_type, "iat": now, "exp": now + timedelta(minutes=10)}, private_key, algorithm="ES256")

    alice = {"Authorization": f"Bearer {token('alice')}"}
    bob = {"Authorization": f"Bearer {token('bob')}"}
    assert client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "long-password"}).status_code == 410
    assert client.get("/api/v1/me", headers=alice).json()["email"] == "alice@example.com"
    created = client.post("/api/v1/accounts", headers=alice, json={"name": "Checking", "currency": "USD", "opening_balance": "100.00"})
    assert created.status_code == 201
    assert len(client.get("/api/v1/accounts", headers=alice).json()) == 1
    assert client.get("/api/v1/accounts", headers=bob).json() == []
    assert client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token('alice', 'another-app')}"}).status_code == 401
    assert client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token('svc_admin')}"}).status_code == 401
    assert client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token('alice', token_type='impersonation')}"}).status_code == 401
