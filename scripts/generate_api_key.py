#!/usr/bin/env python3
"""Generate API keys for customers."""

import secrets
import string
import sys


def generate_api_key(prefix: str = "sk_live_", length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.
    
    Args:
        prefix: Key prefix (default: "sk_live_")
        length: Length of random part (default: 32)
    
    Returns:
        API key string
    """
    # Generate random alphanumeric string
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    return f"{prefix}{random_part}"


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python generate_api_key.py <customer_id> [prefix] [length]")
        print("\nExamples:")
        print("  python generate_api_key.py customer_001")
        print("  python generate_api_key.py customer_002 sk_live_ 32")
        sys.exit(1)
    
    customer_id = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else "sk_live_"
    length = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    
    api_key = generate_api_key(prefix, length)
    
    print(f"\n{'='*60}")
    print(f"Generated API Key for: {customer_id}")
    print(f"{'='*60}")
    print(f"\nCustomer ID: {customer_id}")
    print(f"API Key:     {api_key}")
    print("\nEnvironment Variable Format:")
    print(f"CUSTOMER_API_KEYS={customer_id}:{api_key}")
    print("\nFor multiple customers:")
    print(f"CUSTOMER_API_KEYS={customer_id}:{api_key},customer_002:sk_live_OTHER_KEY")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
