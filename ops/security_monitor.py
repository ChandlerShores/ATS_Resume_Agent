"""Security monitoring utilities to track suspicious activity."""

import time
from collections import defaultdict
from typing import Dict, List

from ops.logging import logger


class SecurityMonitor:
    """Monitor for suspicious activity and security events."""
    
    def __init__(self):
        # Track failed requests per IP
        self.failed_attempts: Dict[str, List[Dict]] = defaultdict(list)
        
        # Track request patterns per IP
        self.request_timestamps: Dict[str, List[float]] = defaultdict(list)
        
        # Track suspicious patterns detected
        self.suspicious_patterns: Dict[str, List[str]] = defaultdict(list)
        
        # Configuration
        self.max_failures_per_hour = 10
        self.max_requests_per_minute = 20
        self.alert_threshold = 5  # Alert after 5 suspicious events
    
    def _cleanup_old_data(self, ip: str):
        """Clean up old data for an IP address."""
        now = time.time()
        
        # Clean up failed attempts older than 1 hour
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip]
            if now - attempt["timestamp"] < 3600
        ]
        
        # Clean up request timestamps older than 1 minute
        self.request_timestamps[ip] = [
            ts for ts in self.request_timestamps[ip]
            if now - ts < 60
        ]
        
        # Clean up suspicious patterns older than 1 hour
        self.suspicious_patterns[ip] = [
            pattern for pattern in self.suspicious_patterns[ip]
            if now - pattern["timestamp"] < 3600
        ]
    
    def log_failed_request(self, ip: str, reason: str, endpoint: str = ""):
        """Log a failed request attempt.
        
        Args:
            ip: Client IP address
            reason: Reason for failure
            endpoint: API endpoint that failed
        """
        self._cleanup_old_data(ip)
        
        attempt = {
            "timestamp": time.time(),
            "reason": reason,
            "endpoint": endpoint
        }
        
        self.failed_attempts[ip].append(attempt)
        
        # Check if this IP should be flagged
        recent_failures = len(self.failed_attempts[ip])
        
        if recent_failures >= self.max_failures_per_hour:
            logger.warning(
                stage="security_monitor",
                msg=f"High failure rate detected from IP {ip}",
                failures=recent_failures,
                threshold=self.max_failures_per_hour,
                recent_reasons=[a["reason"] for a in self.failed_attempts[ip][-5:]]
            )
        
        logger.info(
            stage="security_monitor",
            msg="Failed request logged",
            ip=ip,
            reason=reason,
            endpoint=endpoint,
            total_failures=recent_failures
        )
    
    def log_suspicious_pattern(self, ip: str, pattern: str, input_type: str = ""):
        """Log a suspicious pattern detected in input.
        
        Args:
            ip: Client IP address
            pattern: Suspicious pattern detected
            input_type: Type of input (jd_text, bullets, etc.)
        """
        self._cleanup_old_data(ip)
        
        pattern_event = {
            "timestamp": time.time(),
            "pattern": pattern,
            "input_type": input_type
        }
        
        self.suspicious_patterns[ip].append(pattern_event)
        
        # Check if this IP should be flagged
        recent_patterns = len(self.suspicious_patterns[ip])
        
        if recent_patterns >= self.alert_threshold:
            logger.warning(
                stage="security_monitor",
                msg=f"Multiple suspicious patterns detected from IP {ip}",
                pattern_count=recent_patterns,
                threshold=self.alert_threshold,
                recent_patterns=[p["pattern"] for p in self.suspicious_patterns[ip][-3:]]
            )
        
        logger.info(
            stage="security_monitor",
            msg="Suspicious pattern detected",
            ip=ip,
            pattern=pattern,
            input_type=input_type,
            total_patterns=recent_patterns
        )
    
    def track_request(self, ip: str, endpoint: str = ""):
        """Track a successful request.
        
        Args:
            ip: Client IP address
            endpoint: API endpoint accessed
        """
        self._cleanup_old_data(ip)
        
        now = time.time()
        self.request_timestamps[ip].append(now)
        
        # Check for high request rate
        recent_requests = len(self.request_timestamps[ip])
        
        if recent_requests > self.max_requests_per_minute:
            logger.warning(
                stage="security_monitor",
                msg=f"High request rate detected from IP {ip}",
                requests=recent_requests,
                threshold=self.max_requests_per_minute,
                endpoint=endpoint
            )
    
    def is_ip_suspicious(self, ip: str) -> tuple[bool, List[str]]:
        """Check if an IP address is exhibiting suspicious behavior.
        
        Args:
            ip: IP address to check
            
        Returns:
            Tuple of (is_suspicious, reasons)
        """
        self._cleanup_old_data(ip)
        
        reasons = []
        
        # Check failure rate
        recent_failures = len(self.failed_attempts[ip])
        if recent_failures >= self.max_failures_per_hour:
            reasons.append(f"High failure rate: {recent_failures} failures/hour")
        
        # Check request rate
        recent_requests = len(self.request_timestamps[ip])
        if recent_requests > self.max_requests_per_minute:
            reasons.append(f"High request rate: {recent_requests} requests/minute")
        
        # Check suspicious patterns
        recent_patterns = len(self.suspicious_patterns[ip])
        if recent_patterns >= self.alert_threshold:
            reasons.append(f"Multiple suspicious patterns: {recent_patterns} detected")
        
        return len(reasons) > 0, reasons
    
    def get_security_stats(self) -> Dict[str, any]:
        """Get security monitoring statistics.
        
        Returns:
            Dictionary with security stats
        """
        now = time.time()
        
        # Count active IPs
        active_ips = set()
        for ip in self.failed_attempts.keys():
            if any(now - attempt["timestamp"] < 3600 for attempt in self.failed_attempts[ip]):
                active_ips.add(ip)
        
        for ip in self.request_timestamps.keys():
            if any(now - ts < 60 for ts in self.request_timestamps[ip]):
                active_ips.add(ip)
        
        # Count suspicious IPs
        suspicious_ips = []
        for ip in active_ips:
            is_suspicious, reasons = self.is_ip_suspicious(ip)
            if is_suspicious:
                suspicious_ips.append({"ip": ip, "reasons": reasons})
        
        return {
            "total_active_ips": len(active_ips),
            "suspicious_ips": len(suspicious_ips),
            "suspicious_ip_details": suspicious_ips,
            "total_failed_attempts": sum(len(self.failed_attempts[ip]) for ip in self.failed_attempts),
            "total_suspicious_patterns": sum(len(self.suspicious_patterns[ip]) for ip in self.suspicious_patterns),
            "monitoring_period_hours": 1
        }


# Global instance
security_monitor = SecurityMonitor()
