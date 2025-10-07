"""Custom exceptions for resume parsing with frontend-friendly error messages."""


class ResumeParsingError(Exception):
    """
    Base exception for all resume parsing errors.
    
    This exception hierarchy enables clear error propagation to frontends,
    allowing UIs to display specific, actionable error messages to users.
    """
    pass


class UnsupportedFormatError(ResumeParsingError):
    """
    Raised when resume file format is not supported.
    
    Supported formats: .docx, .pdf, .txt
    """
    pass


class FileReadError(ResumeParsingError):
    """
    Raised when file cannot be read.
    
    Possible causes:
    - File doesn't exist
    - Insufficient permissions
    - Corrupted file
    - Encoding issues
    """
    pass


class NoBulletsFoundError(ResumeParsingError):
    """
    Raised when no resume bullets could be extracted from the file.
    
    Possible causes:
    - Resume has non-standard formatting
    - Text is embedded in images/tables
    - File is actually empty or contains only header information
    """
    pass


class ValidationError(ResumeParsingError):
    """
    Raised when generated input fails Pydantic validation.
    
    This indicates the parsed data doesn't match the JobInput schema,
    typically due to missing required fields or invalid data types.
    """
    pass

