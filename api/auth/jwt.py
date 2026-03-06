import time

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from api.core.config import settings


# Payload follows RFC 7519
# https://www.rfc-editor.org/rfc/rfc7519#section-4.1
class JWTTokenPayload(BaseModel):
    iss: str
    sub: str
    exp: int
    iat: int


class JWTToken(BaseModel):
    payload: JWTTokenPayload
    access_token: str


def create_jwt_token(user_id: str) -> JWTToken:
    iat = int(time.time())
    exp = iat + settings.jwt_access_token_expire_secs

    token_payload = JWTTokenPayload(
        iss=settings.jwt_issuer,
        sub=user_id,
        exp=exp,
        iat=iat,
    )

    access_token = jwt.encode(
        token_payload.model_dump(),
        key=settings.get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )

    return JWTToken(payload=token_payload, access_token=access_token)


def verify_jwt_token(token: str) -> JWTTokenPayload:
    try:
        raw_payload = jwt.decode(
            token,
            settings.get_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": True},
            issuer=settings.jwt_issuer,
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid: {e}",
        ) from e

    return JWTTokenPayload(**raw_payload)
