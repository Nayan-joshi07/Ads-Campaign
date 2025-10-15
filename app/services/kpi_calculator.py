from typing import List
from app.models.models import DailyStat


class KPICalculator:
    @staticmethod
    def calculate_kpis(stats: List[DailyStat]) -> dict:
        total_impressions = sum(stat.impressions for stat in stats)
        total_clicks = sum(stat.clicks for stat in stats)
        total_conversions = sum(stat.conversions for stat in stats)
        total_spend = sum(stat.spend for stat in stats)
        ctr = (total_clicks / total_impressions) * \
            100 if total_impressions > 0 else 0
        cvr = (total_conversions / total_clicks) * \
            100 if total_clicks > 0 else 0
        cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
        cpa = (total_spend / total_conversions) if total_conversions > 0 else 0
        return {
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_spend": round(total_spend, 2),
            "ctr": round(ctr, 2),
            "cvr": round(cvr, 2),
            "cpc": round(cpc, 2),
            "cpa": round(cpa, 2)
        }
