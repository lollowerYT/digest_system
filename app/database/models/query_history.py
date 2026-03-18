import uuid
from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.database import Base
from app.utils.time_utils import utc_now


class QueryHistory(Base):
    __tablename__ = "query_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    digest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("digests.id"), nullable=False)
    query_params: Mapped[str] = mapped_column(Text, nullable=False)  # JSON строка с параметрами запроса
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="query_history")
    digest: Mapped["Digest"] = relationship("Digest")
