from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.config import get_settings
from db.models import User
from domain.token_schemas import Token, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/token/")


class AuthService:
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        # openssl rand -hex 32
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = expire_minutes

    async def authenticate_user(self, user: User, password: str) -> bool:
        # TODO: check out bcrypt.checkpw(password.encode('utf-8'), hashed_password):, CryptContext throws warnings regarding deprecated code
        if not self.verify_password(password, user.hashed_password):
            raise ValueError("Incorrect password.")

        return True

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(minutes=15)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def decode_token(self, token: str) -> TokenData:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload: dict = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception

        except JWTError:
            raise credentials_exception

        return TokenData(**payload)

    def generate_access_token(self, username: str, session_id: str) -> Token:
        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = self.create_access_token(
            data={"sub": username, "id": session_id},
            expires_delta=access_token_expires,
        )
        return Token(access_token=access_token, token_type="bearer")


async def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
