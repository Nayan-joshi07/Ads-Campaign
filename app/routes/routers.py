from typing import List, Optional
from fastapi import APIRouter, FastAPI, HTTPException, Query
from app.services.health_services import health_monitor
from app.models.models import Campaign, CampaignStatus, CampaignWithKPIs, Channel, DailyStat, EventIngest, HealthResponse
from app.services.kpi_calculator import KPICalculator

router = APIRouter()

campaigns_db: List[Campaign] = [
    Campaign(
        id="cmp_123",
        name="App Install – India",
        status=CampaignStatus.active,
        channel=Channel.meta,
        createdAt="2025-09-15T00:00:00Z",
        stats=[
            DailyStat(date="2025-10-01", impressions=120000,
                      clicks=2400, conversions=180, spend=450.25),
            DailyStat(date="2025-10-02", impressions=115000,
                      clicks=2300, conversions=172, spend=430.50),
            DailyStat(date="2025-10-03", impressions=130000,
                      clicks=2600, conversions=195, spend=487.75)
        ]
    ),
    Campaign(
        id="cmp_456",
        name="Brand Awareness – US",
        status=CampaignStatus.active,
        channel=Channel.google,
        createdAt="2025-09-20T00:00:00Z",
        stats=[
            DailyStat(date="2025-10-01", impressions=250000,
                      clicks=5000, conversions=350, spend=1250.00),
            DailyStat(date="2025-10-02", impressions=245000,
                      clicks=4900, conversions=343, spend=1225.00)
        ]
    ),
    Campaign(
        id="cmp_789",
        name="Lead Gen – Europe",
        status=CampaignStatus.paused,
        channel=Channel.linkedin,
        createdAt="2025-08-10T00:00:00Z",
        stats=[
            DailyStat(date="2025-09-28", impressions=80000,
                      clicks=1600, conversions=120, spend=800.00),
            DailyStat(date="2025-09-29", impressions=82000,
                      clicks=1640, conversions=123, spend=820.00)
        ]
    )
]


@router.get("/campaigns", response_model=dict)
async def get_campaigns(
    status: Optional[CampaignStatus] = None,
    dateFrom: Optional[str] = Query(
        None, description="Filter stats from this date (YYYY-MM-DD)"),
    dateTo: Optional[str] = Query(
        None, description="Filter stats to this date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List campaigns with filters and pagination.
    Returns campaigns with computed KPIs.
    """
    filtered_campaigns = campaigns_db
    # Filter by status
    if status:
        filtered_campaigns = [
            c for c in filtered_campaigns if c.status == status]

    # Filter stats by date range
    result_campaigns = []
    for campaign in filtered_campaigns:
        filtered_stats = campaign.stats

        if dateFrom:
            filtered_stats = [s for s in filtered_stats if s.date >= dateFrom]
        if dateTo:
            filtered_stats = [s for s in filtered_stats if s.date <= dateTo]

        if filtered_stats:
            kpis = KPICalculator.calculate_kpis(filtered_stats)
            campaign_dict = campaign.dict()
            campaign_dict['stats'] = [s.dict() for s in filtered_stats]
            campaign_dict['kpis'] = kpis
            result_campaigns.append(campaign_dict)
    # Pagination
    total = len(result_campaigns)
    paginated = result_campaigns[offset:offset + limit]

    return {
        "data": paginated,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    }


@router.get("/campaigns/{campaign_id}", response_model=CampaignWithKPIs)
async def get_campaign_by_id(campaign_id: str):
    """
    Get campaign details with recent metrics series and computed KPIs.
    """
    campaign = next((c for c in campaigns_db if c.id == campaign_id), None)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Calculate KPIs
    kpis = KPICalculator.calculate_kpis(campaign.stats)

    campaign_dict = campaign.dict()
    campaign_dict['kpis'] = kpis

    return campaign_dict


@router.get("/metrics/summary", response_model=dict)
async def get_metrics_summary(
    status: Optional[CampaignStatus] = None,
    channel: Optional[Channel] = None
):
    """
    Get aggregated metrics across all campaigns.
    Returns totals, averages, CTR, CVR, and best/worst performers.
    """
    filtered_campaigns = campaigns_db

    if status:
        filtered_campaigns = [
            c for c in filtered_campaigns if c.status == status]
    if channel:
        filtered_campaigns = [
            c for c in filtered_campaigns if c.channel == channel]

    if not filtered_campaigns:
        return {
            "totals": {},
            "averages": {},
            "best_performers": {},
            "worst_performers": {}
        }

    # Aggregate all stats
    all_stats = []
    for campaign in filtered_campaigns:
        all_stats.extend(campaign.stats)

    # Calculate overall KPIs
    overall_kpis = KPICalculator.calculate_kpis(all_stats)

    # Find best and worst performers by CTR
    campaign_kpis = []
    for campaign in filtered_campaigns:
        kpis = KPICalculator.calculate_kpis(campaign.stats)
        campaign_kpis.append({
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "ctr": kpis["ctr"],
            "cvr": kpis["cvr"],
            "cpa": kpis["cpa"]
        })

    campaign_kpis.sort(key=lambda x: x["ctr"], reverse=True)

    return {
        "totals": {
            "campaigns": len(filtered_campaigns),
            "impressions": overall_kpis["total_impressions"],
            "clicks": overall_kpis["total_clicks"],
            "conversions": overall_kpis["total_conversions"],
            "spend": overall_kpis["total_spend"]
        },
        "averages": {
            "ctr": overall_kpis["ctr"],
            "cvr": overall_kpis["cvr"],
            "cpc": overall_kpis["cpc"],
            "cpa": overall_kpis["cpa"]
        },
        "best_performers": {
            "highest_ctr": campaign_kpis[0] if campaign_kpis else None,
            "lowest_cpa": min(campaign_kpis, key=lambda x: x["cpa"]) if campaign_kpis else None
        },
        "worst_performers": {
            "lowest_ctr": campaign_kpis[-1] if campaign_kpis else None,
            "highest_cpa": max(campaign_kpis, key=lambda x: x["cpa"]) if campaign_kpis else None
        }
    }


@router.post("/events", status_code=201)
async def ingest_event(event: EventIngest):
    """
    Ingest daily stats to extend the dataset for a campaign.
    """
    campaign = next(
        (c for c in campaigns_db if c.id == event.campaign_id), None)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check if stat for this date already exists
    existing_stat = next(
        (s for s in campaign.stats if s.date == event.date), None)

    if existing_stat:
        raise HTTPException(
            status_code=400, detail=f"Stats for date {event.date} already exist")

    # Add new stat
    new_stat = DailyStat(
        date=event.date,
        impressions=event.impressions,
        clicks=event.clicks,
        conversions=event.conversions,
        spend=event.spend
    )

    campaign.stats.append(new_stat)
    campaign.stats.sort(key=lambda x: x.date)

    return {
        "message": "Event ingested successfully",
        "campaign_id": event.campaign_id,
        "date": event.date
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Service health check with uptime, p95 latency, and error rate.
    """
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(health_monitor.get_uptime(), 2),
        p95_latency_ms=round(health_monitor.get_p95_latency(), 2),
        error_rate=round(health_monitor.get_error_rate(), 2),
        total_requests=health_monitor.total_requests
    )
