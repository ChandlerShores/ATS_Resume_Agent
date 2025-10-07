"""Custom exceptions for resume parsing with frontend-friendly error messages."""


class ResumeParsingError(Exception):
    """
    Base exception for all resume parsing errors.

    This exception hierarchy enables clear error propagation to frontends,
    allowing UIs to display specific, actionable error messages to users.
    """


class UnsupportedFormatError(ResumeParsingError):
    """
    Raised when resume file format is not supported.

    Supported formats: .docx, .pdf, .txt
    """


class FileReadError(ResumeParsingError):
    """
    Raised when file cannot be read.

    Possible causes:
    - File doesn't exist
    - Insufficient permissions
    - Corrupted file
    - Encoding issues
    """


class NoBulletsFoundError(ResumeParsingError):
    """
    Raised when no resume bullets could be extracted from the file.

    Possible causes:
    - Resume has non-standard formatting
    - Text is embedded in images/tables
    - File is actually empty or contains only header information
    """


class ValidationError(ResumeParsingError):
    """
    Raised when generated input fails Pydantic validation.

    This indicates the parsed data doesn't match the JobInput schema,
    typically due to missing required fields or invalid data types.
    """


class JobScrapingError(ResumeParsingError):
    """
    Base exception for job board scraping errors.

    This includes any failure during the process of fetching and
    extracting job posting data from URLs.
    """


class PaywallDetectedError(JobScrapingError):
    """
    Raised when job board requires login to view full posting.

    Common for sites like LinkedIn, Indeed that require authentication.
    User should manually copy-paste the JD text instead.
    """


class InvalidJobURLError(JobScrapingError):
    """
    Raised when URL doesn't point to a valid job posting.

    Possible causes:
    - URL is a company homepage
    - URL is a search results page
    - URL is expired or invalid
    """


class ScrapingTimeoutError(JobScrapingError):
    """
    Raised when scraping operation takes too long.

    This could be due to:
    - Slow network connection
    - Large HTML page
    - LLM API timeout
    """
