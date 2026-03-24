from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Literal


class SDigest(BaseModel):
    id: UUID
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
class SDigestCreate(BaseModel):
    channels: Optional[List[str]] = None
    date_from: date
    date_to: date
    filter_query: Optional[str] = None
    n_clusters: int
    output_format: Literal["text", "audio"] = "text"
