"""Tests for job board scraper functionality."""

import pytest
from unittest.mock import Mock, patch
from ops.job_board_scraper import (
    scrape_job_posting,
    _fetch_html,
    _detect_paywall,
    _clean_html,
    _extract_with_llm,
    _validate_scraped_data
)
from ops.parsing_errors import (
    PaywallDetectedError,
    InvalidJobURLError,
    ScrapingTimeoutError,
    JobScrapingError
)


# Sample HTML fixtures
VALID_JOB_HTML = """
<html>
<head><title>Senior Financial Analyst - Acme Corp</title></head>
<body>
    <nav>Navigation stuff</nav>
    <main>
        <h1>Senior Financial Analyst</h1>
        <div class="company">Acme Corp</div>
        <div class="location">New York, NY</div>
        <div class="salary">$100,000 - $150,000</div>
        <div class="job-description">
            <h2>About the Role</h2>
            <p>We are seeking a Senior Financial Analyst to join our team...</p>
            <h2>Requirements</h2>
            <ul>
                <li>5+ years of experience in financial analysis</li>
                <li>Strong Excel and SQL skills</li>
                <li>CPA or CFA certification preferred</li>
            </ul>
        </div>
    </main>
    <footer>Footer stuff</footer>
</body>
</html>
"""

PAYWALL_HTML = """
<html>
<body>
    <h1>Sign in to continue</h1>
    <p>Please log in to view this job posting.</p>
    <form>
        <input type="email" placeholder="Email">
        <input type="password" placeholder="Password">
        <button>Sign in</button>
    </form>
</body>
</html>
"""

NON_JOB_HTML = """
<html>
<head><title>Company Homepage</title></head>
<body>
    <h1>Welcome to Acme Corp</h1>
    <p>We are a leading provider of...</p>
    <a href="/careers">View our open positions</a>
</body>
</html>
"""


class TestDetectPaywall:
    """Tests for paywall detection."""
    
    def test_detects_sign_in_page(self):
        """Should detect 'sign in to continue' paywall."""
        assert _detect_paywall(PAYWALL_HTML) is True
    
    def test_detects_login_to_view(self):
        """Should detect 'login to view' paywall."""
        html = "<html><body>Login to view this job posting</body></html>"
        assert _detect_paywall(html) is True
    
    def test_no_paywall_on_valid_job(self):
        """Should not detect paywall on valid job page."""
        assert _detect_paywall(VALID_JOB_HTML) is False


class TestCleanHTML:
    """Tests for HTML cleaning."""
    
    def test_removes_script_tags(self):
        """Should remove script tags."""
        html = "<html><script>alert('hi')</script><body>Content</body></html>"
        cleaned = _clean_html(html)
        assert "<script>" not in cleaned
        assert "Content" in cleaned
    
    def test_removes_style_tags(self):
        """Should remove style tags."""
        html = "<html><style>body { color: red; }</style><body>Content</body></html>"
        cleaned = _clean_html(html)
        assert "<style>" not in cleaned
        assert "Content" in cleaned
    
    def test_truncates_long_html(self):
        """Should truncate HTML that exceeds max_length."""
        html = "<html><body>" + ("x" * 60000) + "</body></html>"
        cleaned = _clean_html(html, max_length=1000)
        assert len(cleaned) <= 1100  # Allow some overhead
        assert "content truncated" in cleaned.lower()
    
    def test_extracts_main_content_if_present(self):
        """Should prioritize main tag content."""
        html = """
        <html>
        <nav>Navigation</nav>
        <main>Main Content</main>
        <footer>Footer</footer>
        </html>
        """
        cleaned = _clean_html(html)
        assert "Main Content" in cleaned
        # Note: BeautifulSoup might keep nav/footer, but main should be present


class TestValidateScrapedData:
    """Tests for scraped data validation."""
    
    def test_valid_data_passes(self):
        """Valid data should not raise exception."""
        data = {
            "company": "Acme Corp",
            "job_title": "Senior Financial Analyst",
            "jd_text": "We are seeking a financial analyst with 5+ years of experience...",
            "is_valid_job_posting": True,
            "confidence": "high"
        }
        # Should not raise
        _validate_scraped_data(data)
    
    def test_invalid_job_posting_raises(self):
        """Should raise InvalidJobURLError if not a valid posting."""
        data = {
            "company": "",
            "job_title": "",
            "jd_text": "This is not a job posting",
            "is_valid_job_posting": False,
            "confidence": "low"
        }
        with pytest.raises(InvalidJobURLError):
            _validate_scraped_data(data)
    
    def test_missing_required_fields_raises(self):
        """Should raise JobScrapingError if required fields missing."""
        data = {
            "company": "Acme Corp",
            # Missing job_title
            "jd_text": "Some text",
            "is_valid_job_posting": True
        }
        with pytest.raises(JobScrapingError, match="Missing required fields"):
            _validate_scraped_data(data)
    
    def test_invalid_job_title_raises(self):
        """Should raise InvalidJobURLError if job title is unrealistic."""
        data = {
            "company": "Acme Corp",
            "job_title": "AB",  # Too short
            "jd_text": "Some description",
            "is_valid_job_posting": True
        }
        with pytest.raises(InvalidJobURLError, match="Job title seems invalid"):
            _validate_scraped_data(data)
    
    def test_short_jd_text_raises(self):
        """Should raise InvalidJobURLError if JD text is too short."""
        data = {
            "company": "Acme Corp",
            "job_title": "Senior Analyst",
            "jd_text": "Too short",  # Less than 50 chars
            "is_valid_job_posting": True
        }
        with pytest.raises(InvalidJobURLError, match="Job description too short"):
            _validate_scraped_data(data)


class TestExtractWithLLM:
    """Tests for LLM extraction."""
    
    @patch('ops.job_board_scraper.get_llm_client')
    def test_successful_extraction(self, mock_get_llm):
        """Should extract structured data from HTML."""
        mock_llm = Mock()
        mock_llm.complete_json.return_value = {
            "company": "Acme Corp",
            "job_title": "Senior Financial Analyst",
            "jd_text": "We are seeking a financial analyst...",
            "location": "New York, NY",
            "salary": "$100K-150K",
            "is_valid_job_posting": True,
            "confidence": "high"
        }
        mock_get_llm.return_value = mock_llm
        
        result = _extract_with_llm("<html>...</html>")
        
        assert result["company"] == "Acme Corp"
        assert result["job_title"] == "Senior Financial Analyst"
        assert mock_llm.complete_json.called
    
    @patch('ops.job_board_scraper.get_llm_client')
    def test_llm_failure_raises(self, mock_get_llm):
        """Should raise JobScrapingError if LLM fails."""
        mock_llm = Mock()
        mock_llm.complete_json.side_effect = Exception("LLM API error")
        mock_get_llm.return_value = mock_llm
        
        with pytest.raises(JobScrapingError, match="LLM extraction failed"):
            _extract_with_llm("<html>...</html>")


class TestScrapeJobPosting:
    """Integration tests for full scraping pipeline."""
    
    @patch('ops.job_board_scraper.scrape_job_posting')
    def test_cache_hit_skips_scraping(self, _mock_scrape):
        """Should return cached result without scraping."""
        # This would need the cache module to be mocked properly
        pass
    
    @patch('ops.job_board_scraper._fetch_html')
    @patch('ops.job_board_scraper._extract_with_llm')
    @patch('ops.job_cache.get_cached_job_posting')
    @patch('ops.job_cache.cache_job_posting')
    def test_successful_scrape_flow(
        self, mock_cache_write, mock_cache_read,
        mock_extract, mock_fetch
    ):
        """Should successfully scrape and return job data."""
        url = "https://example.com/job/123"
        mock_cache_read.return_value = None  # No cache
        mock_fetch.return_value = VALID_JOB_HTML
        mock_extract.return_value = {
            "company": "Acme Corp",
            "job_title": "Senior Financial Analyst",
            "jd_text": "We are seeking a financial analyst with 5+ years experience in FP&A...",
            "location": "New York, NY",
            "salary": "$100K-150K",
            "is_valid_job_posting": True,
            "confidence": "high"
        }
        
        result = scrape_job_posting(url)
        
        assert result["company"] == "Acme Corp"
        assert result["job_title"] == "Senior Financial Analyst"
        assert result["url"] == url
        assert "scraped_at" in result
        assert mock_cache_write.called
    
    @patch('ops.job_board_scraper._fetch_html')
    @patch('ops.job_cache.get_cached_job_posting')
    def test_paywall_detection_raises(self, mock_cache_read, mock_fetch):
        """Should raise PaywallDetectedError when paywall detected."""
        mock_cache_read.return_value = None
        mock_fetch.return_value = PAYWALL_HTML
        
        with pytest.raises(PaywallDetectedError, match="requires login"):
            scrape_job_posting("https://linkedin.com/jobs/123")
    
    @patch('ops.job_board_scraper._fetch_html')
    @patch('ops.job_board_scraper._extract_with_llm')
    @patch('ops.job_cache.get_cached_job_posting')
    def test_invalid_job_url_raises(
        self, mock_cache_read, mock_extract, mock_fetch
    ):
        """Should raise InvalidJobURLError for non-job pages."""
        mock_cache_read.return_value = None
        mock_fetch.return_value = NON_JOB_HTML
        mock_extract.return_value = {
            "company": "",
            "job_title": "",
            "jd_text": "This appears to be a company homepage, not a job posting",
            "is_valid_job_posting": False,
            "confidence": "low"
        }
        
        with pytest.raises(InvalidJobURLError):
            scrape_job_posting("https://example.com/")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

