"""VALIDATOR agent: Checks for PII and unsupported claims."""

import re

from ops.llm_client import get_llm_client
from schemas.models import ValidationResult

# PII patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


SYSTEM_PROMPT = """You are a resume quality control expert.

Check bullets for:
1. No unsupported/vague claims ("highly skilled", "expert level" without evidence)
2. No new facts beyond the original bullet

Flag issues but only apply SAFE fixes.
Do NOT modify facts or add new information."""


USER_PROMPT_TEMPLATE = """Validate this revised bullet against the original.

Original: {original}
Revised: {revised}

Check for:
- Unsupported claims (new facts not in original)
- Vague outcomes

Return JSON:
{{
  "ok": true/false,
  "flags": ["issue1", "issue2", ...],
  "safe_fixes": {{"old_phrase": "new_phrase", ...}},
  "corrected_text": "..."
}}"""


class Validator:
    """Agent for validating PII and factual consistency."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()

    def check_pii(self, text: str) -> list[str]:
        """
        Check for PII in text.

        Args:
            text: Text to check

        Returns:
            List[str]: PII issues found
        """
        issues = []

        if EMAIL_PATTERN.search(text):
            issues.append("PII detected: email address")

        if PHONE_PATTERN.search(text):
            issues.append("PII detected: phone number")

        if SSN_PATTERN.search(text):
            issues.append("PII detected: SSN")

        return issues


    def _check_factual_consistency_llm(
        self, original: str, revised: str, jd_signals=None
    ) -> list[str]:
        """
        Use LLM to check if revised bullet stays factually consistent with original.

        This checks for fabrication issues like:
        - Invented hard tools/platforms
        - Activity type mismatches
        - Borrowed metrics from other bullets
        - New facts not in original

        Args:
            original: Original bullet text
            revised: Revised bullet text
            jd_signals: JD signals with categorized keywords (optional)

        Returns:
            List of consistency violation flags
        """
        hard_tools_context = ""
        if jd_signals and jd_signals.hard_tools:
            hard_tools_context = (
                f"\n\nKNOWN HARD TOOLS from JD: {', '.join(jd_signals.hard_tools[:10])}\n"
                f"These are factual claims - flag if added to revised but NOT in original."
            )

        consistency_prompt = f"""Compare these two resume bullets for factual consistency.

Original: "{original}"
Revised:  "{revised}"{hard_tools_context}

Check for these FABRICATION TYPES:

1. HARD TOOLS: Specific platforms/tools in revised but NOT in original
   Examples: Marketo, Salesforce, Monday.com, Google Analytics, Figma, Tableau
   
2. ACTIVITY MISMATCH: Fundamental activity changed (e.g., design → marketing)

3. BORROWED METRICS: Numbers in revised that aren't in original

4. INVENTED FACTS: New companies, titles, or achievements not in original

Return JSON:
{{
  "is_consistent": true/false,
  "violations": [
    {{"type": "hard_tool_fabrication", "detail": "Added Marketo which wasn't in original"}},
    {{"type": "borrowed_metric", "detail": "Added $3M which isn't in this bullet"}},
    ...
  ]
}}

If consistent, return: {{"is_consistent": true, "violations": []}}"""

        try:
            response = self.llm_client.complete_json(
                system_prompt="You are a fact-checker ensuring resume edits don't fabricate information.",
                user_prompt=consistency_prompt,
                temperature=0.1,  # Low temperature for consistent checking
            )

            flags = []
            if not response.get("is_consistent", True):
                for violation in response.get("violations", []):
                    flags.append(f"{violation['type']}: {violation['detail']}")

            return flags

        except Exception as e:
            # If LLM check fails, log but don't block
            from ops.logging import logger

            logger.warn(stage="validate", msg=f"Factual consistency check failed: {e}")
            return []

    def validate(
        self, original: str, revised: str, apply_fixes: bool = True, jd_signals=None
    ) -> ValidationResult:
        """
        Validate a revised bullet using PII detection and factual consistency checking.

        Args:
            original: Original bullet
            revised: Revised bullet
            apply_fixes: Whether to apply safe fixes (currently unused)
            jd_signals: JD signals with categorized keywords (optional)

        Returns:
            ValidationResult: Validation results with flags
        """
        from ops.logging import logger
        
        flags = []
        fixes = []
        corrected = revised

        # 1. Check PII
        pii_issues = self.check_pii(revised)
        flags.extend(pii_issues)

        # 2. LLM-based factual consistency check (keep this for hard tool validation)
        if jd_signals:
            consistency_flags = self._check_factual_consistency_llm(original, revised, jd_signals)
            flags.extend(consistency_flags)

        # Determine overall OK status
        ok = len(flags) == 0

        logger.info(
            stage="validator",
            msg=f"Validation completed with {len(flags)} flags",
            flags_count=len(flags),
            fixes_applied=len(fixes)
        )

        return ValidationResult(ok=ok, flags=flags, fixes=fixes), corrected
