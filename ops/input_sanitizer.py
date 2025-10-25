"""Input sanitization utilities to prevent injection attacks."""

import html
import re


class InputSanitizer:
    """Sanitizes user inputs to prevent injection attacks."""

    # Dangerous patterns that could be used for prompt injection
    DANGEROUS_PATTERNS = [
        r"ignore\s+all\s+previous\s+instructions",
        r"forget\s+everything",
        r"you\s+are\s+now",
        r"act\s+as\s+if",
        r"pretend\s+to\s+be",
        r"roleplay\s+as",
        r"system\s+prompt",
        r"assistant\s+prompt",
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"data:text/html",
        r"override\s+your\s+instructions",
        r"disregard\s+previous\s+instructions",
        r"new\s+instructions:",
        r"you\s+must\s+now",
        r"your\s+new\s+role\s+is",
        r"forget\s+your\s+training",
        r"ignore\s+your\s+training",
    ]

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 50000) -> str:
        """Sanitize text input to prevent injection attacks.

        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # HTML escape to prevent XSS
        text = html.escape(text)

        # Remove dangerous patterns (case insensitive)
        for pattern in cls.DANGEROUS_PATTERNS:
            text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

        # Limit length
        text = text[:max_length]

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    @classmethod
    def sanitize_bullets(
        cls, bullets: list[str], max_bullets: int = 20, max_bullet_length: int = 1000
    ) -> list[str]:
        """Sanitize bullet list.

        Args:
            bullets: List of bullets to sanitize
            max_bullets: Maximum number of bullets allowed
            max_bullet_length: Maximum length per bullet

        Returns:
            Sanitized list of bullets
        """
        if not bullets:
            return []

        sanitized = []
        for bullet in bullets[:max_bullets]:  # Limit number of bullets
            if bullet and bullet.strip():  # Skip empty bullets
                clean_bullet = cls.sanitize_text(bullet, max_length=max_bullet_length)
                if clean_bullet:  # Only add non-empty sanitized bullets
                    sanitized.append(clean_bullet)

        return sanitized

    @classmethod
    def sanitize_job_description(cls, jd_text: str, max_length: int = 50000) -> str:
        """Sanitize job description text.

        Args:
            jd_text: Job description text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized job description
        """
        return cls.sanitize_text(jd_text, max_length=max_length)

    @classmethod
    def sanitize_role(cls, role: str, max_length: int = 200) -> str:
        """Sanitize job role/title.

        Args:
            role: Job role to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized role
        """
        return cls.sanitize_text(role, max_length=max_length)

    @classmethod
    def sanitize_extra_context(cls, context: str, max_length: int = 5000) -> str:
        """Sanitize extra context.

        Args:
            context: Extra context to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized context
        """
        return cls.sanitize_text(context, max_length=max_length)

    @classmethod
    def detect_suspicious_patterns(cls, text: str) -> list[str]:
        """Detect suspicious patterns in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected suspicious patterns
        """
        detected = []
        text_lower = text.lower()

        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower):
                detected.append(f"Potential injection pattern: {pattern}")

        return detected

    @classmethod
    def is_safe_input(cls, text: str) -> tuple[bool, list[str]]:
        """Check if input is safe and return any warnings.

        Args:
            text: Text to check

        Returns:
            Tuple of (is_safe, warnings)
        """
        warnings = cls.detect_suspicious_patterns(text)

        # Check for excessive length
        if len(text) > 100000:  # 100KB
            warnings.append("Input exceeds safe length limit")

        # Check for suspicious repetition
        if len(set(text.split())) < 10 and len(text) > 1000:
            warnings.append("Input appears to be repetitive or spam")

        is_safe = len(warnings) == 0
        return is_safe, warnings
