from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class SUserProfile(BaseModel):
    id: UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    token_balance: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SUpdateUserTokens(BaseModel):
    amount: int
    operation: Literal["MANUAL_ADD", "MANUAL_SET"]

