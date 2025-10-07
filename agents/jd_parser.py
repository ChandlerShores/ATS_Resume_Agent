"""JD_PARSER agent: Extracts prioritized terms and competencies from job descriptions."""

import re

import httpx

from ops.llm_client import get_llm_client
from ops.retry import RetryableError, retry_with_backoff
from schemas.models import JDSignals

SYSTEM_PROMPT = """You are an expert at analyzing job descriptions and extracting key competencies, skills, and keywords.

Your task is to extract the most important terms that an ATS (Applicant Tracking System) would look for when matching a resume to this job description.

Prioritize:
1. Technical skills and tools
2. Domain expertise and certifications
3. Core competencies and soft skills
4. Industry-specific terminology

Group related terms and provide synonyms to improve matching flexibility."""


USER_PROMPT_TEMPLATE = """Extract and categorize ALL job description keywords from the following job description.

Job Description:
{jd_text}

Return a JSON object with this structure:
{{
  "top_terms": ["term1", "term2", ...],
  "weights": {{"term1": 1.0, "term2": 0.9, ...}},
  "synonyms": {{"term1": ["synonym1", "synonym2"], ...}},
  "themes": {{"theme1": ["term1", "term2"], ...}},
  "soft_skills": ["analytical thinking", "adaptability", ...],
  "hard_tools": ["Marketo", "Google Analytics", ...],
  "domain_terms": ["B2B healthcare", "SaaS", ...]
}}

Guidelines:
- top_terms: Up to 25 most important keywords/phrases
- weights: Importance score 0.0-1.0 (1.0 = must-have, 0.5 = nice-to-have)
- synonyms: Alternative terms that mean the same thing
- themes: Group related terms (e.g., "Technical Skills", "Soft Skills")

CATEGORIZE ALL KEYWORDS into three types:

1. soft_skills: ALL transferable competencies mentioned in JD that can be inferred from work
   Examples (not exhaustive): analytical thinking, problem-solving, communication, adaptability, 
   collaboration, attention to detail, curiosity, stakeholder management
   
2. hard_tools: ALL specific tools/platforms/technologies mentioned in JD (factual claims)
   Examples (not exhaustive): Marketo, Salesforce, Monday.com, Google Analytics, Figma, 
   Tableau, ChatGPT, PowerPoint, Excel
   
3. domain_terms: ALL industry/context terminology mentioned in JD
   Examples (not exhaustive): B2B healthcare, SaaS, multi-channel campaigns, demand generation,
   single-specialty care, patient engagement

IMPORTANT:
- Extract ALL keywords that fit each category, not just examples
- If unsure, categorize conservatively (prefer hard_tool over soft_skill)
- Hard tools are verifiable facts - flag anything with a brand name or specific product
- Domain terms will only be added to bullets if contextually grounded (in original or surrounding bullets)
"""


class JDParser:
    """Agent for parsing job descriptions and extracting signals."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()

    @retry_with_backoff(max_retries=3, exceptions=(httpx.HTTPError, RetryableError))
    def fetch_jd_from_url(self, url: str, use_scraper: bool = True) -> str:
        """
        Fetch job description from URL.

        Args:
            url: URL to fetch JD from
            use_scraper: Use LLM-powered scraper (default True) for clean extraction,
                        or False for raw HTML (backward compatible)

        Returns:
            str: Fetched JD text

        Raises:
            RetryableError: If fetch fails
        """
        if use_scraper:
            # Use LLM-powered scraper for clean extraction
            try:
                from ops.job_board_scraper import scrape_job_posting

                scraped = scrape_job_posting(url)
                return scraped["jd_text"]
            except Exception as e:
                # If scraping fails, log and fall back to raw HTML
                from ops.logging import logger

                logger.warn(
                    stage="jd_parser",
                    msg=f"Scraping failed, falling back to raw HTML: {e}",
                    url=url,
                )
                # Fall through to raw HTML fetch

        # Fallback: raw HTML fetch (backward compatible)
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            raise RetryableError(f"Failed to fetch JD from {url}: {e}")

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for processing.

        Args:
            text: Raw text

        Returns:
            str: Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove HTML tags if present
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()

    def parse(self, jd_text: str | None = None, jd_url: str | None = None) -> JDSignals:
        """
        Parse job description and extract signals.

        Args:
            jd_text: Job description text
            jd_url: URL to fetch JD from (if jd_text not provided)

        Returns:
            JDSignals: Extracted signals

        Raises:
            ValueError: If neither jd_text nor jd_url provided
        """
        # Get JD text
        if jd_url:
            jd_text = self.fetch_jd_from_url(jd_url)

        if not jd_text:
            raise ValueError("Either jd_text or jd_url must be provided")

        # Normalize
        normalized_jd = self.normalize_text(jd_text)

        # Call LLM to extract signals
        user_prompt = USER_PROMPT_TEMPLATE.format(jd_text=normalized_jd[:4000])  # Limit length

        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
        )

        # Convert to JDSignals model
        return JDSignals(
            top_terms=response.get("top_terms", [])[:25],  # Ensure max 25
            weights=response.get("weights", {}),
            synonyms=response.get("synonyms", {}),
            themes=response.get("themes", {}),
            soft_skills=response.get("soft_skills", []),
            hard_tools=response.get("hard_tools", []),
            domain_terms=response.get("domain_terms", []),
        )
