import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(256), nullable=False) # username = link
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    news: Mapped[list["News"]] = relationship("News", back_populates="channel", cascade="all, delete-orphan")
