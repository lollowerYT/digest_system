import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now

class EmbeddingProjection(Base):
    __tablename__ = "embedding_projections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("news.id"), nullable=False)  # unique=True убрано
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clusters.id"), nullable=False)
    digest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("digests.id"), nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    news: Mapped["News"] = relationship("News", back_populates="embedding_projection")
    cluster: Mapped["Cluster"] = relationship("Cluster", back_populates="embedding_projections")
    digest: Mapped["Digest"] = relationship("Digest")  # опционально, если нужно