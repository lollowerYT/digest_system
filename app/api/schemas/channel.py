from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class STelegramChannel(BaseModel):
    id: UUID
    telegram_id: int
    name: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class SChannelAdd(BaseModel):
    link: str
