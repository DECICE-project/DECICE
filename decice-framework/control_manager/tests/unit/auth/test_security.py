import pytest
from fastapi import HTTPException
from jose import jwt

from auth.security import AuthService
from domain.token_schemas import Token, TokenData

TEST_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
TEST_ALGORITHM = "HS256"


@pytest.fixture
def auth_service() -> AuthService:
    """
    Provides a clean, state-isolated instance of AuthService for each test function.
    This is a core principle of good testing practice.
    """
    service = AuthService(
        secret_key=TEST_SECRET_KEY, algorithm=TEST_ALGORITHM, expire_minutes=30
    )

    return service


class TestAuthService:
    """A test suite for the AuthService class."""

    def test_get_password_hash_and_verify_success(self, auth_service: AuthService):
        """
        GIVEN a plain-text password
        WHEN it is hashed and then verified against the original plain-text
        THEN the verification should succeed and return True.
        """
        plain_password = "my-secure-password_123!"
        hashed_password = auth_service.get_password_hash(plain_password)

        assert plain_password != hashed_password
        assert auth_service.verify_password(plain_password, hashed_password) is True

    def test_verify_password_failure(self, auth_service: AuthService):
        """
        GIVEN a hashed password
        WHEN it is verified against an incorrect plain-text password
        THEN the verification should fail and return False.
        """
        correct_password = "my-secure-password_123!"
        wrong_password = "not-the-right-password"
        hashed_password = auth_service.get_password_hash(correct_password)

        assert auth_service.verify_password(wrong_password, hashed_password) is False

    def test_create_and_decode_access_token(self, auth_service: AuthService):
        """
        GIVEN a data payload for a JWT
        WHEN an access token is created from it and subsequently decoded
        THEN the decoded payload should match the original data.
        """
        username = "testuser"
        session_id = "test-session-id-xyz"
        data_to_encode = {"sub": username, "id": session_id}

        token_str = auth_service.create_access_token(data=data_to_encode)

        decoded_payload = jwt.decode(
            token_str, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )

        assert decoded_payload["sub"] == username
        assert decoded_payload["id"] == session_id
        assert "exp" in decoded_payload

    def test_decode_token_valid_token(self, auth_service: AuthService):
        """
        GIVEN a valid, correctly structured JWT
        WHEN the decode_token method is called
        THEN it should return a TokenData object with the correct attributes.
        """
        username = "valid_user"
        session_id = "valid_session"
        token_str = auth_service.create_access_token(
            data={"sub": username, "id": session_id}
        )

        token_data = auth_service.decode_token(token_str)

        assert isinstance(token_data, TokenData)
        assert token_data.sub == username
        assert token_data.id == session_id

    def test_decode_token_raises_exception_for_missing_sub(
        self, auth_service: AuthService
    ):
        """
        GIVEN a JWT that is correctly signed but missing the 'sub' (subject) claim
        WHEN the decode_token method is called
        THEN it must raise an HTTPException indicating a credential validation failure.
        """
        payload_without_sub = {"id": "some-session-id"}
        malformed_token = jwt.encode(
            payload_without_sub,
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_service.decode_token(malformed_token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"

    def test_decode_token_raises_exception_for_invalid_signature(
        self, auth_service: AuthService
    ):
        """
        GIVEN a JWT that has been tampered with or signed with a different secret key
        WHEN the decode_token method is called
        THEN it must raise an HTTPException due to the JWTError.
        """
        payload = {"sub": "user", "id": "session"}
        token = auth_service.create_access_token(data=payload)

        wrong_key_service = AuthService(
            secret_key="a-completely-different-and-wrong-secret-key-should-have-64-chars",
            algorithm="HS256",
            expire_minutes=30,
        )

        with pytest.raises(HTTPException) as exc_info:
            wrong_key_service.decode_token(token)

        assert exc_info.value.status_code == 401

    def test_generate_access_token_structure(self, auth_service: AuthService):
        """
        GIVEN a username and session ID
        WHEN the generate_access_token helper is called
        THEN it should return a structured Token object with the correct token_type.
        """
        username = "api_user"
        session_id = "api_session_123"

        token_model = auth_service.generate_access_token(username, session_id)

        assert isinstance(token_model, Token)
        assert token_model.token_type == "bearer"
        assert isinstance(token_model.access_token, str)

        decoded_payload = auth_service.decode_token(token_model.access_token)
        assert decoded_payload.sub == username
        assert decoded_payload.id == session_id
