"""LLM-powered job board scraper for extracting structured job posting data."""

from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ops.llm_client import get_llm_client
from ops.logging import logger
from ops.parsing_errors import (
    InvalidJobURLError,
    JobScrapingError,
    PaywallDetectedError,
    ScrapingTimeoutError,
)
from ops.retry import RetryableError, retry_with_backoff

SYSTEM_PROMPT = """You are a job posting parser that extracts structured data from HTML.

Your task is to analyze HTML from a job posting page and extract key information.
Focus on the actual job description content, ignoring navigation, ads, and footer elements.

If the page appears to be a login page or doesn't contain a job posting, indicate this clearly."""


USER_PROMPT_TEMPLATE = """Extract the following fields from this job posting HTML:

Required fields:
- company: The company name
- job_title: The job title/position
- jd_text: The full job description text (include requirements, responsibilities, qualifications, and all job-related details)

Optional fields (extract if available):
- location: Work location (city, state, or "Remote")
- salary: Salary range if listed

Also indicate:
- is_valid_job_posting: true if this appears to be a real job posting, false if it's a login page, search results, or other non-job page
- confidence: Your confidence level (high/medium/low) that this is a valid job posting

HTML (truncated):
{html_content}

Return valid JSON with this structure:
{{
  "company": "...",
  "job_title": "...",
  "jd_text": "...",
  "location": "...",
  "salary": "...",
  "is_valid_job_posting": true,
  "confidence": "high"
}}

If this is not a valid job posting, set is_valid_job_posting to false and explain why in jd_text."""


def _fetch_html(url: str, timeout: float = 30.0) -> str:
    """
    Fetch raw HTML from URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        str: Raw HTML content

    Raises:
        ScrapingTimeoutError: If request times out
        JobScrapingError: If fetch fails
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.TimeoutException:
        raise ScrapingTimeoutError(f"Request timed out after {timeout}s: {url}")
    except httpx.HTTPError as e:
        raise JobScrapingError(f"Failed to fetch URL: {e}")


def _detect_paywall(html: str) -> bool:
    """
    Detect if HTML is a paywall/login page.

    Args:
        html: Raw HTML content

    Returns:
        bool: True if paywall detected
    """
    # Convert to lowercase for case-insensitive matching
    html_lower = html.lower()

    # Common paywall indicators
    paywall_keywords = [
        "sign in to continue",
        "create an account",
        "login to view",
        "please log in",
        "sign up to see",
        "member login",
        "authentication required",
        "access denied",
    ]

    for keyword in paywall_keywords:
        if keyword in html_lower:
            return True

    return False


def _clean_html(html: str, max_length: int = 50000) -> str:
    """
    Clean and truncate HTML for LLM processing.

    Removes scripts, styles, and other junk while preserving job content.

    Args:
        html: Raw HTML content
        max_length: Maximum character length to keep

    Returns:
        str: Cleaned HTML
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove junk tags
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Try to find main content area (common patterns)
    main_content = None
    for selector in ["main", "article", '[role="main"]', ".job-description", ".job-details"]:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # Use main content if found, otherwise use full body
    content = main_content if main_content else soup.body
    if not content:
        content = soup

    # Get text with some structure preserved
    html_str = str(content)

    # Truncate if too long (keep first part, job content usually at top)
    if len(html_str) > max_length:
        html_str = html_str[:max_length] + "\n\n[... content truncated ...]"

    return html_str


def _extract_with_llm(html: str) -> dict[str, Any]:
    """
    Extract structured data from HTML using LLM.

    Args:
        html: Cleaned HTML content

    Returns:
        Dict with extracted fields

    Raises:
        JobScrapingError: If LLM extraction fails
    """
    try:
        llm_client = get_llm_client()

        user_prompt = USER_PROMPT_TEMPLATE.format(html_content=html)

        response = llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, temperature=0.3, max_tokens=4000
        )

        return response

    except Exception as e:
        raise JobScrapingError(f"LLM extraction failed: {e}")


def _validate_scraped_data(data: dict[str, Any]) -> None:
    """
    Validate scraped data and raise appropriate errors.

    Args:
        data: Scraped data from LLM

    Raises:
        InvalidJobURLError: If not a valid job posting
        JobScrapingError: If required fields missing
    """
    # Check if valid job posting
    if not data.get("is_valid_job_posting", True):
        reason = data.get("jd_text", "Unknown reason")
        raise InvalidJobURLError(f"URL doesn't appear to be a job posting: {reason}")

    # Warn on low confidence
    confidence = data.get("confidence", "unknown")
    if confidence == "low":
        logger.warn(
            stage="scrape_job", msg="Low confidence in extraction quality", confidence=confidence
        )

    # Check required fields
    required_fields = ["company", "job_title", "jd_text"]
    missing_fields = [f for f in required_fields if not data.get(f)]

    if missing_fields:
        raise JobScrapingError(f"Missing required fields: {', '.join(missing_fields)}")

    # Basic sanity checks
    job_title = data.get("job_title", "")
    if len(job_title) < 3 or len(job_title) > 200:
        raise InvalidJobURLError(f"Job title seems invalid: '{job_title}'")

    jd_text = data.get("jd_text", "")
    if len(jd_text) < 50:
        raise InvalidJobURLError(
            f"Job description too short ({len(jd_text)} chars), may not be a real posting"
        )


@retry_with_backoff(max_retries=2, exceptions=(RetryableError,))
def scrape_job_posting(url: str, use_cache: bool = True) -> dict[str, Any]:
    """
    Scrape job posting from URL and extract structured data.

    Main entry point for job board scraping. Fetches HTML, extracts
    structured data using LLM, and returns cleaned job information.

    Args:
        url: Job posting URL
        use_cache: Whether to use cached results (default True)

    Returns:
        Dict with keys:
        - company: Company name
        - job_title: Job title/position
        - jd_text: Full job description text
        - location: Work location (optional)
        - salary: Salary range (optional)
        - raw_html: Original HTML (for debugging)
        - scraped_at: ISO timestamp
        - url: Original URL

    Raises:
        PaywallDetectedError: If login required
        InvalidJobURLError: If not a valid job posting
        ScrapingTimeoutError: If operation times out
        JobScrapingError: For other scraping failures
    """
    logger.info(stage="scrape_job", msg="Starting job scraping", url=url)

    # Check cache first
    if use_cache:
        from ops.job_cache import get_cached_job_posting

        cached = get_cached_job_posting(url)
        if cached:
            logger.info(stage="scrape_job", msg="Using cached job posting", url=url)
            return cached

    try:
        # Fetch HTML
        logger.info(stage="scrape_job", msg="Fetching HTML", url=url)
        raw_html = _fetch_html(url)

        # Detect paywall
        if _detect_paywall(raw_html):
            raise PaywallDetectedError(
                "This job board requires login. Please copy-paste the JD text manually."
            )

        # Clean HTML
        logger.info(stage="scrape_job", msg="Cleaning HTML")
        cleaned_html = _clean_html(raw_html)

        # Extract with LLM
        logger.info(stage="scrape_job", msg="Extracting data with LLM")
        extracted = _extract_with_llm(cleaned_html)

        # Validate
        _validate_scraped_data(extracted)

        # Build result
        result = {
            "company": extracted.get("company", "").strip(),
            "job_title": extracted.get("job_title", "").strip(),
            "jd_text": extracted.get("jd_text", "").strip(),
            "location": extracted.get("location", "").strip() or None,
            "salary": extracted.get("salary", "").strip() or None,
            "raw_html": raw_html,
            "scraped_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "url": url,
        }

        logger.info(
            stage="scrape_job",
            msg="Scraping successful",
            company=result["company"],
            job_title=result["job_title"],
            jd_length=len(result["jd_text"]),
        )

        # Cache result
        if use_cache:
            from ops.job_cache import cache_job_posting

            cache_job_posting(url, result)

        return result

    except (PaywallDetectedError, InvalidJobURLError, ScrapingTimeoutError):
        # Re-raise specific errors as-is
        raise

    except Exception as e:
        # Wrap unexpected errors
        logger.error(stage="scrape_job", msg=f"Unexpected error during scraping: {str(e)}", url=url)
        raise JobScrapingError(f"Failed to scrape job posting: {e}")
