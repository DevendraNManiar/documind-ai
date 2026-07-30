import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.rate_limit import enforce_rate_limit
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    subject = decode_token(token)
    if subject is None:
        raise _CREDENTIALS_EXC
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise _CREDENTIALS_EXC
    user = await db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    return user


async def rate_limited_user(user: User = Depends(get_current_user)) -> User:
    """Same as get_current_user but enforces the per-plan rate limit."""
    await enforce_rate_limit(user)
    return user
