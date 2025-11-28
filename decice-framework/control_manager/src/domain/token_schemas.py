from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    # session_id: str
    token_type: str


class TokenData(BaseModel):
    sub: str
    id: str
    exp: int
