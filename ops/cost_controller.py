"""Cost control utilities to prevent OpenAI API abuse."""

import os
from datetime import datetime, timedelta

from ops.logging import logger


class CostController:
    """Control OpenAI API costs and prevent abuse."""

    def __init__(self):
        # Get limits from environment variables
        self.daily_limit = float(os.getenv("MAX_DAILY_COST", "100.0"))  # $100/day default
        self.request_limit = int(
            os.getenv("MAX_REQUESTS_PER_DAY", "1000")
        )  # 1000 requests/day default

        # In-memory tracking (replace with Redis/DB in production)
        self.daily_costs: dict[str, float] = {}  # date -> cost
        self.daily_requests: dict[str, int] = {}  # date -> count

        # Rough cost estimates per request (varies by model and input size)
        self.cost_per_request = {
            "gpt-4o-mini": 0.01,  # ~$0.01 per request
            "gpt-4-turbo-preview": 0.05,  # ~$0.05 per request
            "gpt-4": 0.10,  # ~$0.10 per request
            "default": 0.05,  # Default estimate
        }

    def _get_today_key(self) -> str:
        """Get today's date key for tracking."""
        return datetime.now().strftime("%Y-%m-%d")

    def _cleanup_old_data(self):
        """Remove data older than 7 days."""
        cutoff_date = datetime.now() - timedelta(days=7)
        cutoff_key = cutoff_date.strftime("%Y-%m-%d")

        # Clean up old cost data
        old_dates = [date for date in self.daily_costs if date < cutoff_key]
        for date in old_dates:
            del self.daily_costs[date]

        # Clean up old request data
        old_dates = [date for date in self.daily_requests if date < cutoff_key]
        for date in old_dates:
            del self.daily_requests[date]

    def can_make_request(self, model: str = "default") -> bool:
        """Check if a request can be made without exceeding limits.

        Args:
            model: LLM model being used

        Returns:
            True if request is allowed, False otherwise
        """
        is_allowed, _ = self.check_cost_limit(model)
        return is_allowed

    def check_cost_limit(self, model: str = "default") -> tuple[bool, str]:
        """Check if request would exceed cost limits.

        Args:
            model: LLM model being used

        Returns:
            Tuple of (is_allowed, reason)
        """
        self._cleanup_old_data()

        today = self._get_today_key()
        current_cost = self.daily_costs.get(today, 0.0)
        current_requests = self.daily_requests.get(today, 0)

        # Check request limit
        if current_requests >= self.request_limit:
            return False, f"Daily request limit exceeded ({current_requests}/{self.request_limit})"

        # Estimate cost for this request
        estimated_cost = self.cost_per_request.get(model, self.cost_per_request["default"])

        # Check cost limit
        if current_cost + estimated_cost > self.daily_limit:
            return (
                False,
                f"Daily cost limit would be exceeded (${current_cost + estimated_cost:.2f} > ${self.daily_limit})",
            )

        return True, "Request allowed"

    def track_request(self, model: str = "default", actual_cost: float | None = None):
        """Track a request for cost monitoring.

        Args:
            model: LLM model used
            actual_cost: Actual cost if known, otherwise estimated
        """
        self._cleanup_old_data()

        today = self._get_today_key()

        # Track request count
        self.daily_requests[today] = self.daily_requests.get(today, 0) + 1

        # Track cost
        cost = (
            actual_cost
            if actual_cost is not None
            else self.cost_per_request.get(model, self.cost_per_request["default"])
        )
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + cost

        logger.info(
            stage="cost_control",
            msg="Request tracked",
            model=model,
            cost=cost,
            daily_total=self.daily_costs[today],
            daily_requests=self.daily_requests[today],
        )

    def get_daily_stats(self) -> dict[str, any]:
        """Get daily usage statistics.

        Returns:
            Dictionary with usage stats
        """
        self._cleanup_old_data()

        today = self._get_today_key()
        current_cost = self.daily_costs.get(today, 0.0)
        current_requests = self.daily_requests.get(today, 0)

        return {
            "date": today,
            "daily_cost": current_cost,
            "daily_requests": current_requests,
            "cost_limit": self.daily_limit,
            "request_limit": self.request_limit,
            "cost_remaining": max(0, self.daily_limit - current_cost),
            "requests_remaining": max(0, self.request_limit - current_requests),
            "cost_percentage": (current_cost / self.daily_limit) * 100,
            "request_percentage": (current_requests / self.request_limit) * 100,
        }

    def is_approaching_limit(self) -> tuple[bool, list[str]]:
        """Check if approaching daily limits.

        Returns:
            Tuple of (is_approaching, warnings)
        """
        stats = self.get_daily_stats()
        warnings = []

        # Warn at 80% of limits
        if stats["cost_percentage"] >= 80:
            warnings.append(
                f"Cost limit: {stats['cost_percentage']:.1f}% used (${stats['daily_cost']:.2f}/${stats['cost_limit']})"
            )

        if stats["request_percentage"] >= 80:
            warnings.append(
                f"Request limit: {stats['request_percentage']:.1f}% used ({stats['daily_requests']}/{stats['request_limit']})"
            )

        return len(warnings) > 0, warnings


# Global instance
cost_controller = CostController()
