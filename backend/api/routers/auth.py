"""
Auth router — handles user registration and login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import UserCreate, UserResponse, Token
from api.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from db.database import get_db
from db import crud

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
