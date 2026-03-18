import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, FLOAT

from app.database.database import Base
from app.utils.time_utils import utc_now


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("news.id"), nullable=False, unique=True)
    vector: Mapped[list[float]] = mapped_column(ARRAY(FLOAT), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    news: Mapped["News"] = relationship("News", back_populates="embedding")
