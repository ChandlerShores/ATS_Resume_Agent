"""Extract quantifiable metrics from resume bullets using regex patterns."""

import re
from typing import Dict, Any, List
from ops.logging import logger


# Regex patterns for metrics extraction
PERCENTAGE_PATTERN = r'(\d+(?:\.\d+)?)\s*%'
DOLLAR_PATTERN = r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([KkMmBb])?'
NUMBER_WITH_CONTEXT_PATTERN = r'(\d+(?:,\d{3})*)\s+([\w\s]+?)(?:\s|,|;|\.|\))'
TIME_PERIOD_PATTERN = r'(\d+)\s+(year|month|week|day|quarter|yr|mo)s?'

# Keywords that indicate meaningful metrics
METRIC_KEYWORDS = [
    'revenue', 'sales', 'profit', 'cost', 'saving', 'reduction', 'increase',
    'growth', 'improvement', 'efficiency', 'productivity', 'accuracy',
    'users', 'customers', 'clients', 'entities', 'reports', 'dashboards',
    'team', 'people', 'employees', 'projects', 'systems', 'processes',
]


def extract_metrics(bullets: List[str]) -> Dict[str, Any]:
    """
    Extract quantifiable metrics from resume bullets.
    
    This is a best-effort extraction using regex patterns. Results may contain
    some noise and should be manually reviewed. If extraction fails, returns
    empty dict (non-critical failure).
    
    Args:
        bullets: List of resume bullets
        
    Returns:
        Dict with keys:
            - percentages: List[str] - Found percentages
            - dollar_amounts: List[str] - Found dollar amounts
            - counts: Dict[str, int] - Numbers with context
            - time_periods: List[str] - Time period mentions
            - raw_numbers: List[int] - All extracted numbers
    """
    try:
        combined_text = ' '.join(bullets)
        
        metrics = {
            'percentages': extract_percentages(combined_text),
            'dollar_amounts': extract_dollar_amounts(combined_text),
            'counts': extract_counts(bullets),
            'time_periods': extract_time_periods(combined_text),
        }
        
        # Log extraction summary
        total_metrics = (
            len(metrics['percentages']) +
            len(metrics['dollar_amounts']) +
            len(metrics['counts']) +
            len(metrics['time_periods'])
        )
        
        if total_metrics > 0:
            logger.info(
                stage="extract_metrics",
                msg=f"Extracted {total_metrics} metrics",
                counts=metrics
            )
        
        return metrics
    
    except Exception as e:
        logger.warn(
            stage="extract_metrics",
            msg=f"Metrics extraction failed: {str(e)}"
        )
        return {}


def extract_percentages(text: str) -> List[str]:
    """
    Extract percentage values from text.
    
    Examples: "31%", "increased by 45%", "95.5% accuracy"
    
    Args:
        text: Text to search
        
    Returns:
        List of percentage strings (e.g., ["31%", "45%"])
    """
    matches = re.findall(PERCENTAGE_PATTERN, text)
    percentages = []
    
    for match in matches:
        pct = float(match)
        # Filter reasonable percentages (1-1000%)
        if 1 <= pct <= 1000:
            percentages.append(f"{match}%")
    
    return list(set(percentages))  # Deduplicate


def extract_dollar_amounts(text: str) -> List[str]:
    """
    Extract dollar amounts from text.
    
    Examples: "$2M", "$500K", "$100,000", "saved $1.5B"
    
    Args:
        text: Text to search
        
    Returns:
        List of dollar amount strings (e.g., ["$2M", "$500K"])
    """
    matches = re.findall(DOLLAR_PATTERN, text)
    amounts = []
    
    for amount, suffix in matches:
        # Convert to float and check reasonable range
        amount_num = float(amount.replace(',', ''))
        
        if suffix:
            suffix_upper = suffix.upper()
            if suffix_upper == 'K' and 1 <= amount_num <= 999:
                amounts.append(f"${amount}{suffix_upper}")
            elif suffix_upper == 'M' and 0.1 <= amount_num <= 999:
                amounts.append(f"${amount}{suffix_upper}")
            elif suffix_upper == 'B' and 0.1 <= amount_num <= 999:
                amounts.append(f"${amount}{suffix_upper}")
        else:
            # No suffix - raw dollar amount
            if 1000 <= amount_num <= 10_000_000:  # Reasonable range
                amounts.append(f"${amount}")
    
    return list(set(amounts))  # Deduplicate


def extract_counts(bullets: List[str]) -> Dict[str, Any]:
    """
    Extract numbers with context from bullets.
    
    Examples: "12 entities", "45 users", "15 reports"
    
    Args:
        bullets: List of resume bullets
        
    Returns:
        Dict mapping context to number (e.g., {"entities": 12, "users": 45})
    """
    counts = {}
    
    for bullet in bullets:
        matches = re.findall(NUMBER_WITH_CONTEXT_PATTERN, bullet.lower())
        
        for number_str, context in matches:
            # Clean up context
            context = context.strip().lower()
            
            # Check if context contains a metric keyword
            if any(keyword in context for keyword in METRIC_KEYWORDS):
                # Extract the actual keyword
                for keyword in METRIC_KEYWORDS:
                    if keyword in context:
                        try:
                            number = int(number_str.replace(',', ''))
                            # Reasonable range check
                            if 1 <= number <= 100_000:
                                counts[keyword] = number
                        except ValueError:
                            continue
    
    return counts


def extract_time_periods(text: str) -> List[str]:
    """
    Extract time period mentions from text.
    
    Examples: "3 years", "6 months", "2 quarters"
    
    Args:
        text: Text to search
        
    Returns:
        List of time period strings (e.g., ["3 years", "6 months"])
    """
    matches = re.findall(TIME_PERIOD_PATTERN, text.lower())
    periods = []
    
    for number, unit in matches:
        num = int(number)
        # Reasonable range checks
        if unit.startswith('year') and 1 <= num <= 50:
            periods.append(f"{number} {unit}s" if num > 1 else f"{number} {unit}")
        elif unit.startswith('month') and 1 <= num <= 120:
            periods.append(f"{number} months" if num > 1 else f"{number} month")
        elif unit.startswith('quarter') and 1 <= num <= 40:
            periods.append(f"{number} quarters" if num > 1 else f"{number} quarter")
        elif (unit.startswith('week') or unit.startswith('day')) and 1 <= num <= 365:
            periods.append(f"{number} {unit}s" if num > 1 else f"{number} {unit}")
    
    return list(set(periods))  # Deduplicate


def format_metrics_summary(metrics: Dict[str, Any]) -> str:
    """
    Format metrics into a human-readable summary.
    
    Args:
        metrics: Metrics dict from extract_metrics()
        
    Returns:
        str: Formatted summary
    """
    lines = []
    
    if metrics.get('percentages'):
        lines.append(f"Percentages: {', '.join(metrics['percentages'])}")
    
    if metrics.get('dollar_amounts'):
        lines.append(f"Dollar amounts: {', '.join(metrics['dollar_amounts'])}")
    
    if metrics.get('counts'):
        count_strs = [f"{v} {k}" for k, v in metrics['counts'].items()]
        lines.append(f"Counts: {', '.join(count_strs)}")
    
    if metrics.get('time_periods'):
        lines.append(f"Time periods: {', '.join(metrics['time_periods'])}")
    
    return '\n'.join(lines) if lines else "No metrics extracted"

