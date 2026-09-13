"""Unit tests for password hashing, JWT cryptography, and RBAC user store."""
import unittest
import time
from src.core.security import PasswordHasher, JWTHandler, UserStore

class TestSecurityAuth(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        password = "SecretPassword123!"
        hashed = PasswordHasher.hash_password(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))

        # Verify correct password
        self.assertTrue(PasswordHasher.verify_password(password, hashed))
        # Verify incorrect password
        self.assertFalse(PasswordHasher.verify_password("WrongPassword", hashed))

    def test_jwt_create_and_decode(self):
        token = JWTHandler.create_access_token(
            subject="analyst@docuchat.ai",
            role="analyst",
            extra_claims={"org": "DocuChat"}
        )
        self.assertTrue(isinstance(token, str))

        payload = JWTHandler.decode_access_token(token)
        self.assertEqual(payload["sub"], "analyst@docuchat.ai")
        self.assertEqual(payload["role"], "analyst")
        self.assertEqual(payload["org"], "DocuChat")
        self.assertIn("exp", payload)

    def test_jwt_tampered_token_rejected(self):
        token = JWTHandler.create_access_token(subject="user@test.com", role="user")
        # Tamper with signature
        tampered_token = token[:-4] + "abcd"
        with self.assertRaises(ValueError):
            JWTHandler.decode_access_token(tampered_token)

    def test_jwt_expired_token_rejected(self):
        # Create token that expired 1 minute ago
        token = JWTHandler.create_access_token(
            subject="expired@test.com",
            role="user",
            expires_minutes=-1
        )
        with self.assertRaises(ValueError):
            JWTHandler.decode_access_token(token)

    def test_user_store_authentication(self):
        user = UserStore.authenticate("admin@docuchat.ai", "AdminPass123!")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "admin")

        invalid_auth = UserStore.authenticate("admin@docuchat.ai", "WrongPass")
        self.assertIsNone(invalid_auth)

if __name__ == "__main__":
    unittest.main()
