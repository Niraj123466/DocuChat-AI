"""Cryptographic security utilities: password hashing, JWT tokens, and user credentials."""
from __future__ import annotations

import hmac
import hashlib
import json
import base64
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("security")

class PasswordHasher:
    """Secure password hashing utilizing Bcrypt with PBKDF2 fallback verification."""

    ITERATIONS = 100_000

    @classmethod
    def hash_password(cls, password: str) -> str:
        try:
            import bcrypt
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        except Exception:
            salt = os.urandom(16)
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls.ITERATIONS)
            return f"pbkdf2:sha256:{cls.ITERATIONS}${salt.hex()}${key.hex()}"

    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        try:
            if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
                import bcrypt
                return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

            if "$" in hashed:
                algorithm, salt_hex, key_hex = hashed.split("$")
                salt = bytes.fromhex(salt_hex)
                expected_key = bytes.fromhex(key_hex)
                actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls.ITERATIONS)
                return hmac.compare_digest(actual_key, expected_key)
            return False
        except Exception as e:
            logger.error(f"Error verifying password hash: {e}")
            return False



class JWTHandler:
    """Lightweight, zero-dependency JWT engine utilizing HS256."""

    @classmethod
    def _base64url_encode(cls, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @classmethod
    def _base64url_decode(cls, data: str) -> bytes:
        padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
        return base64.urlsafe_b64decode(data + padding)

    @classmethod
    def create_access_token(
        cls,
        subject: str,
        role: str = "user",
        extra_claims: Optional[Dict[str, Any]] = None,
        expires_minutes: Optional[int] = None
    ) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        exp_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        exp = now + (exp_minutes * 60)

        payload = {
            "sub": subject,
            "role": role,
            "iat": now,
            "exp": exp,
        }
        if extra_claims:
            payload.update(extra_claims)

        encoded_header = cls._base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        encoded_payload = cls._base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

        signature = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        encoded_signature = cls._base64url_encode(signature)

        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    @classmethod
    def decode_access_token(cls, token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed JWT token structure.")

        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        actual_sig = cls._base64url_decode(encoded_signature)

        if not hmac.compare_digest(actual_sig, expected_sig):
            raise ValueError("Invalid JWT signature.")

        payload = json.loads(cls._base64url_decode(encoded_payload).decode("utf-8"))

        if "exp" in payload and payload["exp"] < int(time.time()):
            raise ValueError("JWT token has expired.")

        return payload


class UserStore:
    """In-memory user store for credentials and role management."""

    _users: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def init_defaults(cls):
        if not cls._users:
            cls.register_user("admin@docuchat.ai", "AdminPass123!", role="admin")
            cls.register_user("user@docuchat.ai", "UserPass123!", role="user")

    @classmethod
    def register_user(cls, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        normalized_email = email.lower().strip()
        if normalized_email in cls._users:
            raise ValueError(f"User with email '{normalized_email}' already exists.")

        user_data = {
            "id": f"usr_{hashlib.md5(normalized_email.encode()).hexdigest()[:10]}",
            "email": normalized_email,
            "hashed_password": PasswordHasher.hash_password(password),
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        cls._users[normalized_email] = user_data
        logger.info(f"User registered successfully: {normalized_email} (Role: {role})")
        return user_data

    @classmethod
    def authenticate(cls, email: str, password: str) -> Optional[Dict[str, Any]]:
        cls.init_defaults()
        user = cls._users.get(email.lower().strip())
        if not user:
            return None
        if not PasswordHasher.verify_password(password, user["hashed_password"]):
            return None
        return user

    @classmethod
    def get_by_email(cls, email: str) -> Optional[Dict[str, Any]]:
        cls.init_defaults()
        return cls._users.get(email.lower().strip())

# Initialize default administrative users
UserStore.init_defaults()
