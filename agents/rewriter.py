"""REWRITER agent: Rewrites resume bullets to be ATS-friendly and JD-aligned."""

from typing import List, Dict, Any
from ops.llm_client import get_llm_client
from schemas.models import RewriteVariant, JDSignals


SYSTEM_PROMPT = """You are an expert resume writer specializing in ATS-optimized, impact-focused bullet points.

Your task is to rewrite resume bullets to be:
1. ATS-friendly with job-description-aligned keywords
2. Impact-forward showing outcomes and achievements
3. Concise (≤30 words)
4. Action-verb-first with active voice
5. Using Oxford comma for lists

CRITICAL RULES:
- NEVER invent facts, numbers, companies, or titles
- If metrics are provided, use them EXACTLY as given
- If no metrics provided, keep qualitative but concrete
- Remove filler phrases like "responsible for", "duties included"
- One clear idea per bullet
- No PII (names, emails, phone numbers)"""


USER_PROMPT_TEMPLATE = """Rewrite this resume bullet to align with the target job description.

Original Bullet:
{bullet}

Target Role: {role}

Key JD Terms (prioritize these):
{jd_terms}

Available Metrics:
{metrics}

Extra Context:
{context}

Generate {num_variants} variants (≤{max_words} words each).

Return JSON:
{{
  "variants": [
    {{"text": "...", "rationale": "1-sentence explanation"}},
    ...
  ]
}}

Remember:
- Start with strong action verb
- Include JD-aligned terms naturally
- Show impact/outcome
- Use provided metrics EXACTLY if available
- Never fabricate details"""


class Rewriter:
    """Agent for rewriting resume bullets."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
    
    def rewrite_bullet(
        self,
        bullet: str,
        role: str,
        jd_signals: JDSignals,
        metrics: Dict[str, Any],
        extra_context: str = "",
        max_words: int = 30,
        num_variants: int = 2
    ) -> List[RewriteVariant]:
        """
        Rewrite a single bullet.
        
        Args:
            bullet: Original bullet text
            role: Target role/position
            jd_signals: Extracted JD signals
            metrics: Available metrics
            extra_context: Additional context
            max_words: Maximum words per variant
            num_variants: Number of variants to generate
            
        Returns:
            List[RewriteVariant]: Generated variants
        """
        # Format JD terms
        top_terms = jd_signals.top_terms[:10]  # Top 10 for context
        jd_terms_str = ", ".join(top_terms)
        
        # Format metrics
        metrics_str = "\n".join([f"- {k}: {v}" for k, v in metrics.items()]) if metrics else "None provided"
        
        # Build prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            bullet=bullet,
            role=role,
            jd_terms=jd_terms_str,
            metrics=metrics_str,
            context=extra_context or "None",
            num_variants=num_variants,
            max_words=max_words
        )
        
        # Get LLM response
        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4  # Slightly higher for variety
        )
        
        # Parse variants
        variants = []
        for variant_data in response.get("variants", []):
            variants.append(RewriteVariant(
                text=variant_data.get("text", ""),
                rationale=variant_data.get("rationale", "")
            ))
        
        return variants
    
    def rewrite_all(
        self,
        bullets: List[str],
        role: str,
        jd_signals: JDSignals,
        metrics: Dict[str, Any],
        extra_context: str = "",
        max_words: int = 30,
        num_variants: int = 2
    ) -> Dict[str, List[RewriteVariant]]:
        """
        Rewrite all bullets.
        
        Args:
            bullets: List of original bullets
            role: Target role
            jd_signals: Extracted JD signals
            metrics: Available metrics
            extra_context: Additional context
            max_words: Maximum words per variant
            num_variants: Number of variants to generate
            
        Returns:
            Dict mapping original bullet to variants
        """
        results = {}
        
        for bullet in bullets:
            variants = self.rewrite_bullet(
                bullet=bullet,
                role=role,
                jd_signals=jd_signals,
                metrics=metrics,
                extra_context=extra_context,
                max_words=max_words,
                num_variants=num_variants
            )
            results[bullet] = variants
        
        return results

