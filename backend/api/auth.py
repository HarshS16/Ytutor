"""
Authentication utilities for Ytutor.
Handles password hashing, JWT token generation/verification,
and password reset OTP management.
"""

import os
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db.database import get_db
from db import crud

load_dotenv()

# ── Password Reset OTP Store ──────────────────────────────────────
# In-memory store: { email: { "otp": str, "expires_at": datetime } }
# In production, replace with Redis or a DB table + real email delivery.
_password_reset_store: dict[str, dict] = {}
RESET_OTP_EXPIRE_MINUTES = 10

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-do-not-use-in-prod")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    FastAPI dependency that extracts and verifies the JWT token,
    and returns the current User object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
        
    user = await crud.get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user


# ── Password Reset OTP Functions ──────────────────────────────────

def generate_reset_otp(email: str) -> str:
    """Generate a 6-digit OTP for password reset and store it."""
    otp = f"{secrets.randbelow(1000000):06d}"
    _password_reset_store[email.lower()] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_OTP_EXPIRE_MINUTES),
    }
    return otp


def verify_reset_otp(email: str, otp: str) -> bool:
    """Verify a password reset OTP. Returns True if valid and not expired."""
    entry = _password_reset_store.get(email.lower())
    if not entry:
        return False
    if entry["otp"] != otp:
        return False
    if datetime.now(timezone.utc) > entry["expires_at"]:
        # Expired — clean up
        _password_reset_store.pop(email.lower(), None)
        return False
    return True


def clear_reset_otp(email: str) -> None:
    """Remove the OTP entry after successful password reset."""
    _password_reset_store.pop(email.lower(), None)
