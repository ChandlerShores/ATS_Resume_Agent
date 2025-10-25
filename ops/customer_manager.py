"""Customer management and API key validation for ATS Resume Agent."""

import os
from collections import defaultdict
from datetime import date, datetime

from ops.logging import logger
from schemas.models import Customer, UsageRecord


class CustomerManager:
    """Manages customer API keys and usage tracking."""
    
    def __init__(self):
        self.customers: dict[str, Customer] = {}
        self.usage: dict[str, dict[str, UsageRecord]] = defaultdict(dict)  # customer_id -> date -> usage
        self._load_customers_from_env()
    
    def _load_customers_from_env(self):
        """Load customers from CUSTOMER_API_KEYS environment variable."""
        keys_str = os.getenv("CUSTOMER_API_KEYS", "")
        
        if not keys_str:
            logger.warn(
                stage="customer_manager",
                msg="No CUSTOMER_API_KEYS environment variable found"
            )
            return
        
        try:
            for pair in keys_str.split(","):
                pair = pair.strip()
                if ":" in pair:
                    customer_id, api_key = pair.split(":", 1)
                    customer_id = customer_id.strip()
                    api_key = api_key.strip()
                    
                    customer = Customer(
                        customer_id=customer_id,
                        api_key=api_key,
                        name=f"Customer {customer_id}",
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    
                    self.customers[api_key] = customer
                    
                    logger.info(
                        stage="customer_manager",
                        msg=f"Loaded customer: {customer_id}",
                        customer_id=customer_id
                    )
            
            logger.info(
                stage="customer_manager",
                msg=f"Loaded {len(self.customers)} customers from environment",
                total_customers=len(self.customers)
            )
            
        except Exception as e:
            logger.error(
                stage="customer_manager",
                msg=f"Failed to load customers from environment: {e}",
                error=str(e)
            )
    
    def validate_api_key(self, api_key: str) -> str:
        """
        Validate API key and return customer ID.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Customer ID if valid
            
        Raises:
            ValueError: If API key is invalid
        """
        if not api_key:
            raise ValueError("API key is required")
        
        customer = self.customers.get(api_key)
        if not customer:
            logger.warn(
                stage="customer_manager",
                msg="Invalid API key provided",
                api_key_prefix=api_key[:8] + "..." if len(api_key) > 8 else api_key
            )
            raise ValueError("Invalid API key")
        
        if not customer.is_active:
            logger.warn(
                stage="customer_manager",
                msg="Inactive customer attempted to use API",
                customer_id=customer.customer_id
            )
            raise ValueError("Customer account is inactive")
        
        return customer.customer_id
    
    def track_usage(self, customer_id: str, bullets_count: int):
        """
        Track usage for a customer.
        
        Args:
            customer_id: Customer ID
            bullets_count: Number of bullets processed
        """
        today = date.today().isoformat()
        now = datetime.utcnow()
        
        # Get or create usage record for today
        if today not in self.usage[customer_id]:
            self.usage[customer_id][today] = UsageRecord(
                customer_id=customer_id,
                date=today,
                request_count=0,
                total_bullets=0,
                last_request=now
            )
        
        # Update usage
        usage_record = self.usage[customer_id][today]
        usage_record.request_count += 1
        usage_record.total_bullets += bullets_count
        usage_record.last_request = now
        
        logger.info(
            stage="customer_manager",
            msg="Usage tracked",
            customer_id=customer_id,
            bullets_count=bullets_count,
            daily_requests=usage_record.request_count,
            daily_bullets=usage_record.total_bullets
        )
    
    def get_usage_stats(self, customer_id: str) -> dict[str, any]:
        """
        Get usage statistics for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Dictionary with usage statistics
        """
        today = date.today().isoformat()
        
        # Get today's usage
        today_usage = self.usage[customer_id].get(today)
        
        # Get last 7 days usage
        last_7_days = []
        for i in range(7):
            check_date = date.today().replace(day=date.today().day - i).isoformat()
            if check_date in self.usage[customer_id]:
                usage_record = self.usage[customer_id][check_date]
                last_7_days.append({
                    "date": usage_record.date,
                    "requests": usage_record.request_count,
                    "bullets": usage_record.total_bullets
                })
        
        return {
            "customer_id": customer_id,
            "today": {
                "requests": today_usage.request_count if today_usage else 0,
                "bullets": today_usage.total_bullets if today_usage else 0,
                "last_request": today_usage.last_request.isoformat() if today_usage else None
            },
            "last_7_days": last_7_days,
            "total_days_active": len(self.usage[customer_id])
        }
    
    def get_all_customers_stats(self) -> dict[str, any]:
        """
        Get statistics for all customers.
        
        Returns:
            Dictionary with overall statistics
        """
        today = date.today().isoformat()
        
        total_requests_today = 0
        total_bullets_today = 0
        active_customers_today = 0
        
        for customer_id in self.usage:
            today_usage = self.usage[customer_id].get(today)
            if today_usage:
                total_requests_today += today_usage.request_count
                total_bullets_today += today_usage.total_bullets
                active_customers_today += 1
        
        return {
            "total_customers": len(self.customers),
            "active_customers_today": active_customers_today,
            "total_requests_today": total_requests_today,
            "total_bullets_today": total_bullets_today
        }


# Global customer manager instance
customer_manager = CustomerManager()
