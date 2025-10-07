"""VALIDATOR agent: Checks for grammar, active voice, PII, and unsupported claims."""

import re
from typing import List, Set
from ops.llm_client import get_llm_client
from schemas.models import ValidationResult


# PII patterns
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

# Filler phrases to remove
FILLER_PHRASES = [
    "responsible for",
    "duties included",
    "tasked with",
    "in charge of",
    "helped to",
    "worked on",
    "involved in",
    "participated in"
]

# Passive voice indicators
PASSIVE_INDICATORS = [
    "was responsible",
    "were responsible",
    "was tasked",
    "were tasked",
    "was assigned",
    "were assigned"
]


SYSTEM_PROMPT = """You are a resume quality control expert.

Check bullets for:
1. Active voice (avoid passive constructions)
2. No filler phrases ("responsible for", "duties included")
3. No unsupported/vague claims ("highly skilled", "expert level" without evidence)
4. Proper grammar and punctuation
5. No new facts beyond the original bullet

Flag issues but only apply SAFE fixes (grammar, filler removal).
Do NOT modify facts or add new information."""


USER_PROMPT_TEMPLATE = """Validate this revised bullet against the original.

Original: {original}
Revised: {revised}

Check for:
- Active voice (flag passive constructions)
- Filler phrases
- Unsupported claims (new facts not in original)
- Grammar/punctuation errors
- Vague outcomes

Return JSON:
{{
  "ok": true/false,
  "flags": ["issue1", "issue2", ...],
  "safe_fixes": {{"old_phrase": "new_phrase", ...}},
  "corrected_text": "..."
}}"""


class Validator:
    """Agent for validating and fixing bullet quality issues."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
    
    def check_pii(self, text: str) -> List[str]:
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
    
    def check_filler(self, text: str) -> List[str]:
        """
        Check for filler phrases.
        
        Args:
            text: Text to check
            
        Returns:
            List[str]: Filler phrases found
        """
        text_lower = text.lower()
        found = []
        
        for filler in FILLER_PHRASES:
            if filler in text_lower:
                found.append(f"Filler phrase: '{filler}'")
        
        return found
    
    def check_passive_voice(self, text: str) -> List[str]:
        """
        Check for passive voice indicators.
        
        Args:
            text: Text to check
            
        Returns:
            List[str]: Passive voice issues
        """
        text_lower = text.lower()
        found = []
        
        for passive in PASSIVE_INDICATORS:
            if passive in text_lower:
                found.append(f"Passive phrasing: '{passive}'")
        
        return found
    
    def remove_filler(self, text: str) -> str:
        """
        Remove filler phrases from text.
        
        Args:
            text: Original text
            
        Returns:
            str: Text with filler removed
        """
        result = text
        
        for filler in FILLER_PHRASES:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(filler), re.IGNORECASE)
            result = pattern.sub('', result)
        
        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        # Capitalize first letter if needed
        if result and result[0].islower():
            result = result[0].upper() + result[1:]
        
        return result
    
    def validate(
        self,
        original: str,
        revised: str,
        apply_fixes: bool = True
    ) -> ValidationResult:
        """
        Validate a revised bullet.
        
        Args:
            original: Original bullet
            revised: Revised bullet
            apply_fixes: Whether to apply safe fixes
            
        Returns:
            ValidationResult: Validation results with fixes
        """
        flags = []
        fixes = []
        corrected = revised
        
        # Check PII
        pii_issues = self.check_pii(revised)
        flags.extend(pii_issues)
        
        # Check filler
        filler_issues = self.check_filler(revised)
        flags.extend(filler_issues)
        
        # Check passive voice
        passive_issues = self.check_passive_voice(revised)
        flags.extend(passive_issues)
        
        # Apply safe fixes
        if apply_fixes and filler_issues:
            corrected = self.remove_filler(corrected)
            fixes.append("Removed filler phrases")
        
        # Use LLM for deeper validation
        user_prompt = USER_PROMPT_TEMPLATE.format(
            original=original,
            revised=corrected
        )
        
        try:
            response = self.llm_client.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )
            
            # Merge LLM flags
            llm_flags = response.get("flags", [])
            flags.extend(llm_flags)
            
            # Apply LLM corrections if provided
            if apply_fixes and response.get("corrected_text"):
                corrected = response["corrected_text"]
                if response.get("safe_fixes"):
                    fixes.append("Applied LLM grammar/clarity fixes")
        
        except Exception as e:
            # LLM validation failed, continue with regex checks
            flags.append(f"LLM validation error: {str(e)}")
        
        # Determine overall OK status
        ok = len(flags) == 0
        
        return ValidationResult(
            ok=ok,
            flags=flags,
            fixes=fixes
        ), corrected

