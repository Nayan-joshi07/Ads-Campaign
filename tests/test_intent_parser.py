import pytest
from datetime import datetime, timedelta
from app.services.intent_parser import IntentParser
from app.models.models import ParsedIntent


class TestIntentParser:
    """Test suite for IntentParser class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.parser = IntentParser()

    def test_empty_prompt(self):
        """Test empty or whitespace-only prompts."""
        assert self.parser.parse("").confidence == 0.0
        assert self.parser.parse("   ").confidence == 0.0
        assert self.parser.parse(None) is not None

    def test_sort_intent_parsing(self):
        """Test sorting intent detection."""
        # Top/best keywords
        intent = self.parser.parse("top campaigns by ctr")
        assert intent.sort_by == "ctr"
        assert intent.sort_order == "desc"
        assert "sort" in self.parser.matched_patterns

        intent = self.parser.parse("best performing campaigns")
        assert intent.sort_by == "conversions"
        assert intent.sort_order == "desc"

        # Worst/lowest keywords
        intent = self.parser.parse("worst campaigns by cpa")
        assert intent.sort_by == "cpa"
        assert intent.sort_order == "asc"

        intent = self.parser.parse("lowest ctr campaigns")
        assert intent.sort_by == "ctr"
        assert intent.sort_order == "asc"

    def test_metric_detection(self):
        """Test various metric detection patterns."""
        metrics_tests = [
            ("campaigns by ctr", "ctr"),
            ("sort by cpa", "cpa"),
            ("order by cpc", "cpc"),
            ("by conversions", "conversions"),
            ("campaigns cpm", "cpm"),
            ("highest spend campaigns", "spend"),
        ]
        
        for prompt, expected_metric in metrics_tests:
            intent = self.parser.parse(f"top {prompt}")
            assert intent.sort_by == expected_metric, f"Failed for: {prompt}"

    def test_filter_parsing(self):
        """Test status and channel filter detection."""
        # Status filters
        status_tests = [
            ("active campaigns", "active"),
            ("running campaigns", "active"),
            ("live campaigns", "active"),
            ("paused campaigns", "paused"),
            ("stopped campaigns", "paused"),
            ("inactive campaigns", "paused"),
        ]
        
        for prompt, expected_status in status_tests:
            intent = self.parser.parse(prompt)
            assert intent.filters.get("status") == expected_status, f"Failed for: {prompt}"
            assert "filter" in self.parser.matched_patterns

        # Channel filters
        channel_tests = [
            ("google campaigns", "google"),
            ("meta campaigns", "meta"),
            ("facebook campaigns", "meta"),
            ("linkedin campaigns", "linkedin"),
            ("x campaigns", "x"),
            ("twitter campaigns", "x"),
        ]
        
        for prompt, expected_channel in channel_tests:
            intent = self.parser.parse(prompt)
            assert intent.filters.get("channel") == expected_channel, f"Failed for: {prompt}"

    def test_combined_filters(self):
        """Test multiple filters in one prompt."""
        intent = self.parser.parse("active google campaigns")
        assert intent.filters["status"] == "active"
        assert intent.filters["channel"] == "google"

        intent = self.parser.parse("paused meta campaigns")
        assert intent.filters["status"] == "paused"
        assert intent.filters["channel"] == "meta"

    def test_date_range_parsing(self):
        """Test date range detection."""
        today = datetime.now().date()
        
        # Yesterday
        intent = self.parser.parse("campaigns yesterday")
        yesterday = today - timedelta(days=1)
        assert intent.date_from == yesterday.isoformat()
        assert intent.date_to == yesterday.isoformat()

        # Last N days
        intent = self.parser.parse("last 7 days")
        expected_from = (today - timedelta(days=7)).isoformat()
        assert intent.date_from == expected_from
        assert intent.date_to == today.isoformat()

        # This week
        intent = self.parser.parse("this week")
        monday = today - timedelta(days=today.weekday())
        assert intent.date_from == monday.isoformat()
        assert intent.date_to == today.isoformat()

        # Last week
        intent = self.parser.parse("last week")
        week_ago = (today - timedelta(days=7)).isoformat()
        assert intent.date_from == week_ago
        assert intent.date_to == today.isoformat()

        # This month
        intent = self.parser.parse("this month")
        month_start = today.replace(day=1).isoformat()
        assert intent.date_from == month_start
        assert intent.date_to == today.isoformat()

    def test_limit_parsing(self):
        """Test limit/top-N detection."""
        limit_tests = [
            ("top 5 campaigns", 5),
            ("first 10 campaigns", 10),
            ("limit 3 campaigns", 3),
            ("show 15 campaigns", 15),
        ]
        
        for prompt, expected_limit in limit_tests:
            intent = self.parser.parse(prompt)
            assert intent.limit == expected_limit, f"Failed for: {prompt}"
            assert "limit" in self.parser.matched_patterns

    def test_default_application(self):
        """Test default value application."""
        # "campaign" (singular) should default to limit 1
        intent = self.parser.parse("best campaign")
        assert intent.limit == 1

        # "top" without limit should default to 5
        intent = self.parser.parse("top campaigns")
        assert intent.limit == 5

        # "best" without limit should default to 5
        intent = self.parser.parse("best campaigns")
        assert intent.limit == 5

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        # High confidence: multiple patterns
        intent = self.parser.parse("top 5 active campaigns by ctr last 7 days")
        assert intent.confidence > 0.7

        # Medium confidence: some patterns
        intent = self.parser.parse("active campaigns")
        assert 0.3 <= intent.confidence <= 0.7

        # Low confidence: unclear prompt
        intent = self.parser.parse("show me some random stuff")
        assert intent.confidence < 0.3

        # Zero confidence: no patterns
        intent = self.parser.parse("random nonsense text")
        assert intent.confidence == 0.0

    def test_complex_prompts(self):
        """Test realistic complex prompts."""
        # Complex prompt with all elements
        intent = self.parser.parse("show top 3 active google campaigns by ctr last 30 days")
        assert intent.sort_by == "ctr"
        assert intent.sort_order == "desc"
        assert intent.limit == 3
        assert intent.filters["status"] == "active"
        assert intent.filters["channel"] == "google"
        assert intent.date_from is not None
        assert intent.confidence > 0.7

        # Another complex example
        intent = self.parser.parse("worst 5 paused meta campaigns by cpa this week")
        assert intent.sort_by == "cpa"
        assert intent.sort_order == "asc"
        assert intent.filters["status"] == "paused"
        assert intent.filters["channel"] == "meta"
        assert intent.date_from is not None

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Multiple metrics (should pick first match)
        intent = self.parser.parse("top campaigns by ctr and cpa")
        assert intent.sort_by in ["ctr", "cpa"]

        # Conflicting sort orders (should pick first match)
        intent = self.parser.parse("top worst campaigns")
        assert intent.sort_order in ["desc", "asc"]

        # Very long prompt with few matches
        long_prompt = "this is a very long prompt with many words but few meaningful patterns for campaign analysis"
        intent = self.parser.parse(long_prompt)
        # Should have penalty applied
        assert intent.confidence <= 0.3

    def test_case_insensitivity(self):
        """Test that parsing is case insensitive."""
        intent1 = self.parser.parse("TOP CAMPAIGNS BY CTR")
        intent2 = self.parser.parse("top campaigns by ctr")
        intent3 = self.parser.parse("Top Campaigns By Ctr")
        
        assert intent1.sort_by == intent2.sort_by == intent3.sort_by
        assert intent1.sort_order == intent2.sort_order == intent3.sort_order

    def test_get_hints(self):
        """Test hint generation."""
        hints = self.parser.get_hints()
        assert isinstance(hints, list)
        assert len(hints) > 0
        assert all(isinstance(hint, str) for hint in hints)
        assert any("top" in hint.lower() for hint in hints)

    def test_get_patterns(self):
        """Test pattern documentation."""
        patterns = self.parser.get_patterns()
        assert isinstance(patterns, dict)
        assert "sorting" in patterns
        assert "metrics" in patterns
        assert "status" in patterns
        assert "channels" in patterns
        assert "date_ranges" in patterns
        assert "limits" in patterns

    def test_whitespace_normalization(self):
        """Test that extra whitespace is handled correctly."""
        intent1 = self.parser.parse("top   campaigns    by   ctr")
        intent2 = self.parser.parse("top campaigns by ctr")
        
        assert intent1.sort_by == intent2.sort_by
        assert intent1.sort_order == intent2.sort_order

    def test_partial_matches(self):
        """Test partial pattern matches."""
        # Only sort, no metric specified
        intent = self.parser.parse("top campaigns")
        assert intent.sort_order == "desc"
        assert intent.limit == 5  # default applied

        # Only filter, no sort
        intent = self.parser.parse("active campaigns")
        assert intent.filters["status"] == "active"
        assert intent.sort_by is None

        # Only date, no other patterns
        intent = self.parser.parse("yesterday")
        assert intent.date_from is not None
        assert intent.sort_by is None