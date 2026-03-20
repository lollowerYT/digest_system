import uuid
from datetime import datetime
from sqlalchemy import DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    digest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("digests.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    digest: Mapped["Digest"] = relationship("Digest", back_populates="clusters")
    cluster_news: Mapped[list["ClusterNews"]] = relationship(
        "ClusterNews",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )
    embedding_projections: Mapped[list["EmbeddingProjection"]] = relationship(
        "EmbeddingProjection",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )
