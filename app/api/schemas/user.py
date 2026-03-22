from pydantic import BaseModel, ConfigDict
from uuid import UUID


class SUserProfile(BaseModel):
    id: UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    token_balance: int

    model_config = ConfigDict(from_attributes=True)


class SUpdateUserTokens(BaseModel):
    tokens: int
