import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String, 
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="users")
    digests: Mapped[list["Digest"]] = relationship("Digest", back_populates="user", cascade="all, delete-orphan")
    favorite_digests: Mapped[list["FavoriteDigest"]] = relationship("FavoriteDigest", back_populates="user", cascade="all, delete-orphan")
    token_transactions: Mapped[list["TokenTransaction"]] = relationship("TokenTransaction", back_populates="user", cascade="all, delete-orphan")
    query_history: Mapped[list["QueryHistory"]] = relationship("QueryHistory", back_populates="user", cascade="all, delete-orphan")
