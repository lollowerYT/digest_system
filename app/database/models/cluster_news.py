import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base


class ClusterNews(Base):
    __tablename__ = "cluster_news"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clusters.id"), nullable=False)
    news_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("news.id"), nullable=False)

    cluster: Mapped["Cluster"] = relationship("Cluster", back_populates="cluster_news")
    news: Mapped["News"] = relationship("News")
