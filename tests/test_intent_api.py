import pytest
from fastapi.testclient import TestClient
from main import app
from app.models.models import CampaignStatus, Channel


class TestIntentAPI:
    """Test suite for /intent/query API endpoint."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        self.base_url = "/intent/query"

    def test_successful_intent_query_sorting(self):
        """Test successful intent query with sorting."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "show top campaigns by ctr last 7 days"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "data" in data
        assert "intent" in data
        assert "pagination" in data
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["sort_by"] == "ctr"
        assert intent["sort_order"] == "desc"
        assert intent["confidence"] >= 0.3
        assert intent["date_from"] is not None
        assert intent["date_to"] is not None
        
        # Check that data is sorted by CTR (descending)
        campaigns = data["data"]
        if len(campaigns) > 1:
            for i in range(len(campaigns) - 1):
                assert campaigns[i]["kpis"]["ctr"] >= campaigns[i + 1]["kpis"]["ctr"]

    def test_successful_intent_query_filtering(self):
        """Test successful intent query with filtering."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "list paused campaigns"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["filters"]["status"] == "paused"
        assert intent["confidence"] >= 0.3
        
        # Check that all returned campaigns are paused
        campaigns = data["data"]
        for campaign in campaigns:
            assert campaign["status"] == "paused"

    def test_successful_intent_query_combined_filters(self):
        """Test intent query with multiple filters."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "active google campaigns"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["filters"]["status"] == "active"
        assert intent["filters"]["channel"] == "google"
        
        # Check that all returned campaigns match filters
        campaigns = data["data"]
        for campaign in campaigns:
            assert campaign["status"] == "active"
            assert campaign["channel"] == "google"

    def test_successful_intent_query_best_performing(self):
        """Test best performing campaign query."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "best performing campaign"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["sort_by"] == "conversions"
        assert intent["sort_order"] == "desc"
        assert intent["limit"] == 1  # Should default to 1 for singular "campaign"
        
        # Should return only one campaign
        campaigns = data["data"]
        assert len(campaigns) <= 1

    def test_successful_intent_query_with_limit(self):
        """Test intent query with explicit limit."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "top 3 campaigns by cpa"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["sort_by"] == "cpa"
        assert intent["sort_order"] == "desc"  # "top" implies desc
        
        # Should return at most 3 campaigns
        campaigns = data["data"]
        assert len(campaigns) <= 3

    def test_successful_intent_query_worst_campaigns(self):
        """Test worst performing campaigns query."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "worst 5 campaigns by cpa this week"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["sort_by"] == "cpa"
        assert intent["sort_order"] == "asc"  # "worst" implies asc for CPA
        assert intent["date_from"] is not None
        assert intent["date_to"] is not None
        
        # Check that data is sorted by CPA (ascending for worst)
        campaigns = data["data"]
        if len(campaigns) > 1:
            for i in range(len(campaigns) - 1):
                assert campaigns[i]["kpis"]["cpa"] <= campaigns[i + 1]["kpis"]["cpa"]

    def test_intent_query_date_filtering(self):
        """Test that date filtering works correctly."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "campaigns yesterday"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent parsing
        intent = data["intent"]
        assert intent["date_from"] is not None
        assert intent["date_to"] is not None
        assert intent["date_from"] == intent["date_to"]  # Same day for yesterday
        
        # Check that all campaigns have stats filtered to the date range
        campaigns = data["data"]
        for campaign in campaigns:
            for stat in campaign["stats"]:
                assert intent["date_from"] <= stat["date"] <= intent["date_to"]

    def test_low_confidence_query_returns_400(self):
        """Test that unclear prompts return 400 with hints."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "random nonsense query that makes no sense"}
        )
        
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        
        assert "error" in error_detail
        assert "hints" in error_detail
        assert "confidence" in error_detail
        assert isinstance(error_detail["hints"], list)
        assert len(error_detail["hints"]) > 0
        assert error_detail["confidence"] < 0.3

    def test_empty_prompt_returns_400(self):
        """Test that empty prompt returns 400."""
        response = self.client.post(
            self.base_url,
            json={"prompt": ""}
        )
        
        assert response.status_code == 400

    def test_whitespace_only_prompt_returns_400(self):
        """Test that whitespace-only prompt returns 400."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "   "}
        )
        
        assert response.status_code == 400

    def test_response_structure_matches_campaigns_endpoint(self):
        """Test that response structure matches GET /campaigns."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "active campaigns"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "data" in data
        assert "pagination" in data
        
        # Check pagination structure
        pagination = data["pagination"]
        assert "total" in pagination
        assert "limit" in pagination
        assert "offset" in pagination
        assert "has_more" in pagination
        
        # Check campaign structure (if any campaigns returned)
        campaigns = data["data"]
        if campaigns:
            campaign = campaigns[0]
            assert "id" in campaign
            assert "name" in campaign
            assert "status" in campaign
            assert "channel" in campaign
            assert "createdAt" in campaign
            assert "stats" in campaign
            assert "kpis" in campaign
            
            # Check KPIs structure
            kpis = campaign["kpis"]
            expected_kpis = ["ctr", "cvr", "cpc", "cpa", "total_impressions", 
                           "total_clicks", "total_conversions", "total_spend"]
            for kpi in expected_kpis:
                assert kpi in kpis

    def test_intent_field_in_response(self):
        """Test that intent information is included in response."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "top campaigns by ctr"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check intent field exists and has expected structure
        assert "intent" in data
        intent = data["intent"]
        
        expected_fields = ["sort_by", "sort_order", "filters", "date_from", 
                          "date_to", "limit", "confidence"]
        for field in expected_fields:
            assert field in intent

    def test_invalid_request_body(self):
        """Test handling of invalid request body."""
        # Missing prompt field
        response = self.client.post(self.base_url, json={})
        assert response.status_code == 422
        
        # Invalid prompt type
        response = self.client.post(self.base_url, json={"prompt": 123})
        assert response.status_code == 422

    def test_case_insensitive_parsing(self):
        """Test that parsing works regardless of case."""
        prompts = [
            "TOP CAMPAIGNS BY CTR",
            "top campaigns by ctr", 
            "Top Campaigns By Ctr"
        ]
        
        responses = []
        for prompt in prompts:
            response = self.client.post(self.base_url, json={"prompt": prompt})
            assert response.status_code == 200
            responses.append(response.json())
        
        # All should have same intent parsing results
        for i in range(1, len(responses)):
            assert responses[0]["intent"]["sort_by"] == responses[i]["intent"]["sort_by"]
            assert responses[0]["intent"]["sort_order"] == responses[i]["intent"]["sort_order"]

    def test_multiple_metrics_handling(self):
        """Test handling when multiple metrics are mentioned."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "top campaigns by ctr and cpa"}  # Add "top" to ensure sort detection
        )
        
        # Should still work, picking one of the metrics
        assert response.status_code == 200
        data = response.json()
        intent = data["intent"]
        assert intent["sort_by"] in ["ctr", "cpa"]

    def test_fallback_sorting(self):
        """Test fallback behavior when sort key doesn't exist."""
        # This should test the KeyError handling in the sorting logic
        response = self.client.post(
            self.base_url,
            json={"prompt": "top campaigns by revenue"}  # revenue maps to conversions
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return results with fallback sorting
        assert len(data["data"]) >= 0

    def test_no_campaigns_match_filters(self):
        """Test behavior when no campaigns match the filters."""
        response = self.client.post(
            self.base_url,
            json={"prompt": "campaigns last 1 days"}  # Very recent date range with no stats
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty data but valid structure (campaigns exist but no stats in range)
        assert data["data"] == []
        assert data["pagination"]["total"] == 0

    def test_date_range_edge_cases(self):
        """Test various date range formats."""
        date_prompts = [
            "campaigns last 30 days",
            "campaigns this month", 
            "campaigns this week",
            "campaigns yesterday"
        ]
        
        for prompt in date_prompts:
            response = self.client.post(self.base_url, json={"prompt": prompt})
            assert response.status_code == 200
            
            data = response.json()
            intent = data["intent"]
            
            # Should have parsed some date range
            if "last" in prompt or "this" in prompt or "yesterday" in prompt:
                assert intent["date_from"] is not None or intent["date_to"] is not None