import uuid
from datetime import datetime, date
from sqlalchemy import Date, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    filter_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    cluster_count: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="digests")
    clusters: Mapped[list["Cluster"]] = relationship("Cluster", back_populates="digest", cascade="all, delete-orphan")
    
