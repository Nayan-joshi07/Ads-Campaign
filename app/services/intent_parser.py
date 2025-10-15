from app.models.models import ParsedIntent
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import re


class IntentParser:
    """A class to parse user intents from text input."""

    # Class constants for pattern matching
    SORT_KEYWORDS = {
        'top': 'desc',
        'best': 'desc',
        'highest': 'desc',
        'worst': 'asc',
        'lowest': 'asc',
        'bottom': 'asc'
    }

    METRICS = [
        'ctr', 'cpa', 'cpc', 'cpm', 'conversions', 'clicks', 
        'impressions', 'spend', 'revenue', 'roas'
    ]

    STATUS_KEYWORDS = {
        'active': 'active',
        'running': 'active',
        'live': 'active',
        'paused': 'paused',
        'stopped': 'paused',
        'inactive': 'paused'
    }

    CHANNEL_KEYWORDS = {
        'meta': 'meta',
        'facebook': 'meta',
        'google': 'google',
        'linkedin': 'linkedin',
        'x': 'x',
        'twitter': 'x'
    }

    def __init__(self):
        """Initialize the parser with empty matched patterns list."""
        self.matched_patterns = []

    def _preprocess(self, prompt: str) -> str:
        """
        Clean and normalize the prompt.

        Steps:
            - Convert to lowercase
            - Strip leading/trailing whitespace
            - Normalize multiple spaces to single space
        """
        prompt = prompt.lower().strip()
        prompt = re.sub(r'\s+', ' ', prompt)
        return prompt

    def _match_sort(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Sort Intent Matcher

        Detects what to sort by and in which direction.

        Pattern Detection:
            - Sort keywords: top, best, worst, lowest, etc.
            - Metric extraction: by [metric] or [metric] alone
            - Special case: "performing" → defaults to conversions

        Examples:
            "top campaigns by ctr" → ('ctr', 'desc')
            "worst by cpa" → ('cpa', 'asc')
            "best performing" → ('conversions', 'desc')

        Returns:
            Tuple of (metric, order) or (None, None)
        """
        sort_order = None

        # Check for sort keywords
        for keyword, order in self.SORT_KEYWORDS.items():
            if keyword in prompt:
                sort_order = order
                break

        # If we found a sort keyword, find the metric
        if sort_order:
            for metric in self.METRICS:
                # Look for patterns like "by ctr", "ctr ", or ending with "ctr"
                if re.search(rf'by\s+{metric}|\s{metric}\s|{metric}$', prompt):
                    return metric, sort_order

            # Special case: "performing" without explicit metric
            if 'performing' in prompt or 'performance' in prompt:
                return 'conversions', sort_order
            
            # If sort keyword found but no metric, return sort order with default metric
            return 'ctr', sort_order

        return None, None

    def _match_filters(self, prompt: str) -> Dict[str, str]:
        """
        Filter Intent Matcher

        Detects status and channel filters.

        Status Detection:
            - active, running, live → 'active'
            - paused, stopped, inactive → 'paused'

        Channel Detection:
            - meta, facebook → 'meta'
            - google → 'google'
            - linkedin → 'linkedin'
            - x, twitter → 'x'

        Examples:
            "active campaigns" → {'status': 'active'}
            "google campaigns" → {'channel': 'google'}
            "paused meta campaigns" → {'status': 'paused', 'channel': 'meta'}

        Returns:
            Dictionary of filters
        """
        filters = {}

        # Check status
        for keyword, status in self.STATUS_KEYWORDS.items():
            if re.search(rf'\b{keyword}\b', prompt):
                filters['status'] = status
                break

        # Check channel
        for keyword, channel in self.CHANNEL_KEYWORDS.items():
            if re.search(rf'\b{keyword}\b', prompt):
                filters['channel'] = channel
                break

        return filters

    def _match_dates(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Date Range Matcher

        Detects temporal references and converts to date ranges.

        Supported Patterns:
            - "yesterday" → yesterday's date
            - "last N days" → N days ago to today
            - "past week" / "last week" → 7 days ago to today
            - "this week" → Monday to today
            - "past month" / "last 30 days" → 30 days ago to today
            - "this month" → First of month to today

        Examples:
            "yesterday" → ('2025-10-14', '2025-10-14')
            "last 7 days" → ('2025-10-08', '2025-10-15')
            "this week" → ('2025-10-13', '2025-10-15')  # If today is Wed

        Returns:
            Tuple of (date_from, date_to) in ISO format or (None, None)
        """
        today = datetime.now().date()

        # Yesterday
        if 'yesterday' in prompt:
            yesterday = today - timedelta(days=1)
            return yesterday.isoformat(), yesterday.isoformat()

        # Last N days
        match = re.search(r'last\s+(\d+)\s+days?', prompt)
        if match:
            days = int(match.group(1))
            return (today - timedelta(days=days)).isoformat(), today.isoformat()

        # Past/last week
        if re.search(r'(past|last)\s+week', prompt):
            return (today - timedelta(days=7)).isoformat(), today.isoformat()

        # This week (Monday to today)
        if 'this week' in prompt:
            monday = today - timedelta(days=today.weekday())
            return monday.isoformat(), today.isoformat()

        # Past/last month or 30 days
        if re.search(r'(past|last)\s+(month|30\s+days?)', prompt):
            return (today - timedelta(days=30)).isoformat(), today.isoformat()

        # This month
        if 'this month' in prompt:
            return today.replace(day=1).isoformat(), today.isoformat()

        return None, None

    def _match_limit(self, prompt: str) -> Optional[int]:
        """
        Limit/Top-N Matcher

        Extracts numeric limits from the prompt.

        Patterns:
            - "top N" → N
            - "first N" → N
            - "limit N" → N
            - "show N" → N

        Examples:
            "top 5 campaigns" → 5
            "first 10" → 10
            "limit 3" → 3

        Returns:
            Integer limit or None
        """
        patterns = [
            r'top\s+(\d+)',
            r'first\s+(\d+)',
            r'limit\s+(\d+)',
            r'show\s+(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt)
            if match:
                return int(match.group(1))

        return None

    def _apply_defaults(self, intent: ParsedIntent, prompt: str) -> ParsedIntent:
        """
        Apply sensible defaults based on context.

        Rules:
            1. If "campaign" (singular) mentioned → limit to 1 (highest priority)
            2. If "top" or "best" mentioned without limit → default to 5
            3. If sorting but no explicit limit → show all (no default)

        Examples:
            "top campaigns" → limit = 5
            "best campaign" → limit = 1
            "sort by ctr" → no limit applied
        """
        # If "campaign" (singular) mentioned, limit to 1 (highest priority)
        if re.search(r'\bcampaign\b(?!s)', prompt) and not intent.limit:
            intent.limit = 1
        # If "top" or "best" mentioned without limit, default to 5
        elif any(k in prompt for k in ['top', 'best']) and not intent.limit:
            intent.limit = 5

        return intent

    def _calc_confidence(self, prompt: str) -> float:
        """
        Calculate confidence score based on what was matched.

        Scoring:
            - Base: 0.3 if any patterns matched
            - Sort: +0.25
            - Filter: +0.20
            - Date: +0.15
            - Limit: +0.10
            - Multiple patterns (3+): +0.10 bonus
            - Long prompt with few matches: -0.20 penalty

        Returns:
            Float between 0.0 and 1.0
        """
        if not self.matched_patterns:
            return 0.0

        score = 0.3  # Base score

        # Add points for each matched pattern
        weights = {
            'sort': 0.25,
            'filter': 0.2,
            'date': 0.15,
            'limit': 0.1
        }

        for pattern in self.matched_patterns:
            score += weights.get(pattern, 0)

        # Bonus for multiple intents (more specific query)
        if len(self.matched_patterns) >= 3:
            score += 0.1

        # Penalty if prompt is very long but few matches (likely unclear)
        word_count = len(prompt.split())
        if word_count > 10 and len(self.matched_patterns) <= 1:
            score -= 0.2

        # Clamp between 0 and 1
        return max(0.0, min(1.0, score))

    def get_hints(self) -> List[str]:
        """
        Generate helpful hints for users when intent is unclear.

        Returns:
            List of example queries
        """
        return [
            "Try: 'show top 5 campaigns by ctr'",
            "Try: 'list paused campaigns'",
            "Try: 'best performing campaign last 7 days'",
            "Try: 'worst campaigns by cpa this week'",
            "Try: 'show active google campaigns'",
            "Try: 'top 10 campaigns by conversions yesterday'"
        ]

    def get_patterns(self) -> Dict[str, List[str]]:
        """
        Return all supported patterns for documentation.

        Useful for error messages and API documentation.

        Returns:
            Dictionary mapping pattern types to supported values
        """
        return {
            "sorting": list(self.SORT_KEYWORDS.keys()),
            "metrics": self.METRICS,
            "status": list(set(self.STATUS_KEYWORDS.values())),
            "channels": list(set(self.CHANNEL_KEYWORDS.values())),
            "date_ranges": [
                "yesterday",
                "last N days",
                "this week",
                "last week",
                "this month",
                "last 30 days"
            ],
            "limits": ["top N", "first N", "limit N"]
        }

    def parse(self, prompt: str) -> ParsedIntent:
        """
        Main parsing method that orchestrates all matchers.

        Process:
            1. Preprocess the prompt (lowercase, normalize whitespace)
            2. Run all pattern matchers in parallel
            3. Apply defaults based on context
            4. Calculate confidence score

        Args:
            prompt: Natural language query string

        Returns:
            ParsedIntent object with all detected intents
        """
        if not prompt or not prompt.strip():
            return ParsedIntent(confidence=0.0)

        # Preprocess
        clean_prompt = self._preprocess(prompt)

        # Initialize intent
        intent = ParsedIntent()
        self.matched_patterns = []

        # Run all matchers
        sort_by, sort_order = self._match_sort(clean_prompt)
        if sort_by:
            intent.sort_by = sort_by
            intent.sort_order = sort_order
            self.matched_patterns.append("sort")

        filters = self._match_filters(clean_prompt)
        if filters:
            intent.filters = filters
            self.matched_patterns.append("filter")

        date_from, date_to = self._match_dates(clean_prompt)
        if date_from:
            intent.date_from = date_from
            intent.date_to = date_to
            self.matched_patterns.append("date")

        limit = self._match_limit(clean_prompt)
        if limit:
            intent.limit = limit
            self.matched_patterns.append("limit")

        # Apply defaults for common patterns
        intent = self._apply_defaults(intent, clean_prompt)

        # Calculate confidence
        intent.confidence = self._calc_confidence(clean_prompt)

        return intent


if __name__ == "__main__":
    parser = IntentParser()
    
    # Test queries
    test_prompts = [
        "show top campaigns by ctr last 7 days",
        "list paused campaigns",
        "best performing campaign",
        "worst 5 campaigns by cpa this week",
        "active google campaigns"
    ]
    
    for prompt in test_prompts:
        intent = parser.parse(prompt)
        print(f"\nPrompt: {prompt}")
        print(f"Parsed: {intent.model_dump()}")
        print(f"Confidence: {intent.confidence:.2f}")
        print(f"Patterns matched: {parser.matched_patterns}")
