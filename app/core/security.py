"""
security.py – JWT & password-hashing utilities for dealer authentication.

Dependencies (already installed):
    python-jose[cryptography]   → JWT encode / decode
    passlib[bcrypt]             → password hashing
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# ── Configuration ────────────────────────────────────────────────────
SECRET_KEY = "changeme-use-env-in-production"   # TODO: load from env / .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ── Password hashing ────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against its stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT token ────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT.

    Parameters
    ----------
    data : dict
        Payload claims (e.g. {"sub": dealer_id}).
    expires_delta : timedelta, optional
        Custom lifetime; defaults to ACCESS_TOKEN_EXPIRE_MINUTES (60 min).

    Returns
    -------
    str
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── JWT dependency (protected routes) ────────────────────────────────
bearer_scheme = HTTPBearer()


def get_current_dealer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> int:
    """
    FastAPI dependency — extracts and validates the JWT from the
    Authorization: Bearer <token> header.

    Returns
    -------
    int
        The authenticated dealer's ID (from the ``sub`` claim).

    Raises
    ------
    HTTPException 401
        If the token is missing, expired, or malformed.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        dealer_id: str | None = payload.get("sub")
        if dealer_id is None:
            raise JWTError("Missing sub claim")
        return int(dealer_id)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    FastAPI dependency — decodes JWT and returns the full User ORM object.

    Requires ``app.db.session.get_db`` to be injected at the router level.
    """
    from app.db.session import get_db
    from app.models.user import User

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing sub claim")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve a DB session via the generator
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # ── Trial-expiry check (runs on every authenticated request) ──
        from app.core.trial import enforce_trial_expiry
        enforce_trial_expiry(user.dealer_id, db)

        return user
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
