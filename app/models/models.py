from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class CampaignStatus(str, Enum):
    active = "active"
    paused = "paused"


class Channel(str, Enum):
    meta = "meta"
    google = "google"
    x = "x"
    linkedin = "linkedin"


class DailyStat(BaseModel):
    date: str
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    conversions: int = Field(ge=0)
    spend: float = Field(ge=0)


class Campaign(BaseModel):
    id: str
    name: str
    status: CampaignStatus
    channel: Channel
    createdAt: str
    stats: List[DailyStat]


class CampaignWithKPIs(BaseModel):
    id: str
    name: str
    status: CampaignStatus
    channel: Channel
    createdAt: str
    stats: List[DailyStat]
    kpis: dict


class EventIngest(BaseModel):
    campaign_id: str
    date: str
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    conversions: int = Field(ge=0)
    spend: float = Field(ge=0)


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    p95_latency_ms: float
    error_rate: float
    total_requests: int
