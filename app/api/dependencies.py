import jwt

from fastapi import Depends,HTTPException,status

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.dependencies import db_get
from app.models.user import User
from app.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

def get_current_user(token:str = Depends(oauth2_scheme),db:Session = Depends(db_get))-> User:
    exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise exception

        user_id = int(user_id)

    except(
        jwt.InvalidTokenError,
        ValueError,
    ): raise exception


    repository = UserRepository(db)

    user = repository.get_by_id(user_id)

    if user is None:
        raise exception

    if not user.is_active:
        raise HTTPException(
            status_code= status.HTTP_403_FORBIDDEN,
            detail="Inactive User"
        )


    return user


