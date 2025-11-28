import logging
import time
from pathlib import Path

import jwt
from fastapi import Depends

from config.settings import SlurmClientSettings, get_settings

logger = logging.getLogger(__name__)

TOKEN_LIFESPAN_SECONDS = 120


class TokenServiceError(Exception):
    """Base class for token-related errors."""


class TokenConnectionError(TokenServiceError):
    """Raised when the service cannot initialize due to missing configuration."""


class TokenResponseError(TokenServiceError):
    """Raised when token generation fails."""


class TokenService:
    """
    Generates Slurm-compatible JWTs internally.
    """

    def __init__(self, secret_key: bytes, algorithm: str):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def request_token(self, username: str) -> str:
        """
        Creates and signs a JWT for the specified user.
        """
        now = int(time.time())
        payload = {
            "exp": now + TOKEN_LIFESPAN_SECONDS,
            "iat": now,
            "sun": username,  # slurm user name (sun)
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            if isinstance(token, bytes):
                token = token.decode("utf-8")
            return token
        except Exception as e:
            logger.error(f"Failed to generate JWT for user {username}: {e}")
            raise TokenResponseError(f"Token generation failed: {e}")


def get_token_service(
    settings: SlurmClientSettings = Depends(get_settings),
) -> TokenService:
    """
    FastAPI dependency provider for TokenService.
    Reads the JWT key from the configured file path.
    """
    key_path = settings.SLURM_JWT_KEY_PATH
    try:
        private_key = Path(key_path).read_bytes()
        return TokenService(secret_key=private_key, algorithm=settings.SLURM_JWT_ALGO)
    except FileNotFoundError:
        logger.critical(f"FATAL: Slurm JWT key file NOT found at: {key_path}")
        raise TokenConnectionError(f"JWT key file not found at {key_path}")
    except PermissionError:
        logger.critical(
            f"FATAL: Insufficient permissions to read JWT key at: {key_path}"
        )
        raise TokenConnectionError(f"Cannot read JWT key at {key_path}")
    except Exception as e:
        logger.critical(f"FATAL: Unexpected error reading JWT key from {key_path}: {e}")
        raise TokenConnectionError(f"Failed to read JWT key: {e}")
