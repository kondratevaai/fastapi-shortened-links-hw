from sqlalchemy.sql import func
from datetime import datetime, timedelta
# from typing import AsyncGenerator, List, Optional
from typing import Optional
from sqlalchemy import String, Integer, select, delete, TIMESTAMP, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import enum


class Base(DeclarativeBase):
    pass


class UserRole(enum.Enum):
    
    USER = "user"
    ADMIN = "admin"


class User(Base):
    # database model for user representation:
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    age: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.USER,
        index=True
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email}, role={self.role})>"


class ShortenedLink(Base):
    # database model to store shortened links:
    __tablename__ = "shortened_links"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    short_code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    original_url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    custom_alias: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    click_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True
    )

    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )

    def __repr__(self) -> str:
        return f"<ShortenedLink(id={self.id}, short_code={self.short_code}, clicks={self.click_count})>"


class UserRequests(Base):
    # database model to log user requests:

    __tablename__ = "user_requests"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False
    )

    text_raw: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    prediction: Mapped[int] = mapped_column(
        nullable=False,
        index=True
    )

    processing_time_ms: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        index=True,
    )

    text_length: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<UserRequests(id={self.id}, user_id={self.user_id}, timestamp={self.timestamp})>"
