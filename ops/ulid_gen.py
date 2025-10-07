"""ULID generation utility for creating unique, sortable job IDs."""

from ulid import ULID


def generate_job_id() -> str:
    """
    Generate a new ULID for job identification.
    
    ULIDs are lexicographically sortable and encode timestamp information,
    making them ideal for tracking job execution order.
    
    Returns:
        str: A new ULID string
    """
    return str(ULID())


def is_valid_ulid(ulid_str: str) -> bool:
    """
    Check if a string is a valid ULID.
    
    Args:
        ulid_str: String to validate
        
    Returns:
        bool: True if valid ULID, False otherwise
    """
    try:
        ULID.from_str(ulid_str)
        return True
    except (ValueError, AttributeError):
        return False

