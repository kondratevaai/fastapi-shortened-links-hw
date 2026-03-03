from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from domain.models import User, UserRole
from schemas.schemas import UserBase, UserResponse, UserRegistrationResponse
from auth.dependencies import get_admin_user
from core.security import create_access_token


router = APIRouter(
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register new user and return JWT token"
)
async def register_user(
    user_data: UserBase,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user_data.email} already exists"
        )

    db_user = User(
        name=user_data.name,
        email=user_data.email,
        age=user_data.age,
        role=UserRole.USER
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    token = create_access_token(db_user.id, db_user.role)

    return {
        "user": db_user,
        "access_token": token,
        "token_type": "bearer"
    }


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Get all users",
    description="Retrieve all users from the database (Admin only)"
)
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> List[User]:
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return list(users)
