"""
Auth router — handles user registration, login, and password reset.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import (
    UserCreate, UserResponse, Token,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse,
)
from api.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    generate_reset_otp,
    verify_reset_otp,
    clear_reset_otp,
)
from db.database import get_db
from db import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email exists
    if await crud.get_user_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    # Check if username exists
    if await crud.get_user_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=400,
            detail="This username is already taken."
        )
        
    hashed_password = get_password_hash(user_in.password)
    user = await crud.create_user(
        db=db,
        email=user_in.email,
        username=user_in.username,
        password_hash=hashed_password
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, getting an access token for future requests.
    Using email as the username field in the form.
    """
    # Find user by email
    user = await crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Get current logged-in user profile."""
    return current_user


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset OTP.
    Always returns success to prevent email enumeration.
    In dev mode, the OTP is included in the response.
    """
    user = await crud.get_user_by_email(db, email=request.email)

    if user:
        otp = generate_reset_otp(request.email)
        logger.info(f"Password reset OTP generated for {request.email}: {otp}")
        # In dev mode, return the OTP directly.
        # In production, send via email and remove otp from response.
        return ForgotPasswordResponse(
            message="If an account with that email exists, a reset code has been sent.",
            otp=otp,
        )

    # Email doesn't exist — still return success (prevent enumeration)
    return ForgotPasswordResponse(
        message="If an account with that email exists, a reset code has been sent.",
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using the OTP received from forgot-password.
    """
    # Verify OTP
    if not verify_reset_otp(request.email, request.otp):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code. Please request a new one.",
        )

    # Find the user
    user = await crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code. Please request a new one.",
        )

    # Update password
    new_hash = get_password_hash(request.new_password)
    await crud.update_user_password(db, user_id=user.id, new_password_hash=new_hash)

    # Clear the OTP
    clear_reset_otp(request.email)

    logger.info(f"Password successfully reset for {request.email}")
    return ResetPasswordResponse(message="Password has been reset successfully. You can now log in.")

