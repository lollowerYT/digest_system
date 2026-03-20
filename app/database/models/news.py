import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class News(Base):
    __tablename__ = "news"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("telegram_channels.id"), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    channel: Mapped["TelegramChannel"] = relationship("TelegramChannel", back_populates="news")
    embedding: Mapped["Embedding"] = relationship("Embedding", back_populates="news", uselist=False)
    embedding_projection: Mapped["EmbeddingProjection"] = relationship(
        "EmbeddingProjection",
        back_populates="news",
        uselist=False  # one-to-one
    )
