from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


def hash_password(password: str, iterations: int = 120_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iter_s, salt_b64, hash_b64 = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_s)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def create_access_token(
    *,
    user_id: int,
    username: str,
    role: str,
    secret: str,
    expires_hours: int = 168,
) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + expires_hours * 3600,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def decode_access_token(token: str, secret: str) -> dict | None:
    try:
        body, sig = token.rsplit(".", 1)
        expect = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        pad = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode((body + pad).encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
