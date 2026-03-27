from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SFavoriteDigest(BaseModel):
    id: UUID
    digest_id: UUID
    user_id: UUID
    title: Optional[str] = None
    summary_text: Optional[str] = None
    filter_query: Optional[str] = None
    date_from: date
    date_to: date
    cluster_count: int
    audio_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
