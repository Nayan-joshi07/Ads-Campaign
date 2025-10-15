from typing import List, Optional, Dict
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


class ParsedIntent(BaseModel):
    """
    Structured representation of parsed user intent.

    Attributes:
        sort_by: Metric to sort by (ctr, cvr, cpc, cpa, conversions, etc.)
        sort_order: 'asc' or 'desc'
        filters: Dictionary of filters (status, channel)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
        limit: Number of results to return
        confidence: Float 0-1 indicating parsing confidence
    """
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None  # 'asc' or 'desc'
    filters: Dict[str, str] = {}
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = None
    confidence: float = 0.0


class IntentQueryRequest(BaseModel):
    """Request model for intent-based query endpoint."""
    prompt: str = Field(description="Natural language query prompt")
