import uuid
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class SUserActivityResponse(BaseModel):
    period: datetime
    user_id: uuid.UUID | str
    requests_count: int


class SUserRegistrationsResponse(BaseModel):
    period: datetime
    registrations: int


class SSystemMetricsResponse(BaseModel):
    period: datetime
    total_requests: int
    avg_response_time: float
    errors: str
