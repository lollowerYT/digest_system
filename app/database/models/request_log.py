import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime
from app.database.database import Base
from app.utils.time_utils import utc_now


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String)
    method: Mapped[str] = mapped_column(String)
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utc_now)
