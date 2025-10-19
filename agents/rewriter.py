"""REWRITER agent: Rewrites resume bullets to be ATS-friendly and JD-aligned."""

from typing import Any

from ops.llm_client import get_llm_client
from schemas.models import JDSignals, RewriteVariant

SYSTEM_PROMPT = """You are an expert resume editor specializing in ATS-optimized, impact-focused bullets.

CORE PHILOSOPHY: You are EDITING, not writing from scratch. Preserve factual accuracy above all else.

Your task is to rewrite resume bullets to be:
1. ATS-friendly with relevant job-description keywords
2. Impact-forward showing outcomes and achievements
3. Concise (≤30 words)
4. Action-verb-first with active voice
5. Using Oxford comma for lists

CRITICAL RULES TO PREVENT FABRICATION:

1. METRICS RULE: Only use metrics provided for THIS SPECIFIC BULLET. Never borrow from other bullets.

2. TOOLS/PLATFORMS RULE: Only mention tools if they appear in the original bullet. Adding new tool names is fabrication.

3. ACTIVITIES RULE: Preserve the core activity. If they did "user research," don't rewrite it as "marketing campaigns."

4. TRANSFERABLE SKILLS: When the bullet doesn't directly map to target role:
   - Identify the underlying skill (e.g., "user research" = "customer insights")
   - Use role-appropriate terminology for that skill
   - Keep the activity type consistent (research stays research, not campaigns)

5. WHEN IN DOUBT: Favor accuracy over keyword optimization. A factually correct bullet with fewer keywords beats a keyword-stuffed fabrication.

EXAMPLES OF CORRECT ADAPTATION:
- "Led UX research" → "Led customer research to inform product decisions" (same activity, different framing)
- "Built prototypes in Figma" → "Built prototypes to validate product concepts" (kept tool, made impact clearer)
- "Increased dashboard usage 34%" → "Increased dashboard usage 34%" (keep metrics exactly as-is)

EXAMPLES OF FABRICATION TO AVOID:
- "Led UX research" → "Executed marketing campaigns using Marketo" (invented activity, invented tool)
- "Built design system" → "Achieved 34% growth and $3M revenue" (borrowed unrelated metrics)
- "User research" → "Demand generation campaigns" (completely changed activity type)"""


USER_PROMPT_TEMPLATE = """Rewrite this resume bullet to align with the target job description while preserving factual accuracy.

Original Bullet:
{bullet}

Target Role: {role}

JD KEYWORDS (use appropriately):

✅ SOFT SKILLS (ADD if the bullet demonstrates them):
{soft_skills}

❌ HARD TOOLS (NEVER add unless in original bullet):
{hard_tools}

✅ DOMAIN TERMS (ADD ONLY if in original bullet or surrounding context):
{domain_terms}

Metrics from THIS BULLET ONLY:
{metrics}

Extra Context:
{context}

REWRITING RULES:

1. SOFT SKILLS: If the work demonstrates a soft skill, weave it in naturally
   Example: "Synthesized 40+ research sessions" → "Applied analytical thinking to synthesize..."

2. HARD TOOLS: ONLY mention if in original bullet - adding them is fabrication
   Example: Original has "Figma" → Can keep "Figma"
   Example: Original has no tools → CANNOT add "Marketo" or "Monday.com"

3. DOMAIN TERMS: ADD ONLY if already in original bullet or clearly implied by surrounding context
   Example: Original mentions "healthcare" → Can add "B2B healthcare"
   Example: Original has no industry context → DO NOT add domain terms

REWRITING PROCESS:

Step 1: What did the person ACTUALLY do in this bullet?
Step 2: What transferable skills does this work demonstrate?
Step 3: What role-appropriate terminology conveys the same activity?
Step 4: Which soft skills can be inferred? Which domain terms are already present?
Step 5: How can we highlight impact using ONLY the metrics provided?

Generate {num_variants} variants (≤{max_words} words each).

Return JSON:
{{
  "variants": [
    {{
      "text": "...",
      "rationale": "Explain what was preserved vs. adapted, and why any changes are factually accurate"
    }},
    ...
  ]
}}

REMEMBER: Soft skills = infer if demonstrated. Hard tools = NEVER fabricate. Domain terms = ONLY if contextually grounded."""


class Rewriter:
    """Agent for rewriting resume bullets."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()

    def rewrite_bullet(
        self,
        bullet: str,
        role: str,
        jd_signals: JDSignals,
        metrics: dict[str, Any],
        extra_context: str = "",
        max_words: int = 30,
        num_variants: int = 2,
    ) -> list[RewriteVariant]:
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
        # Format categorized keywords
        soft_skills_str = (
            ", ".join(jd_signals.soft_skills[:8]) if jd_signals.soft_skills else "None identified"
        )
        hard_tools_str = (
            ", ".join(jd_signals.hard_tools[:8]) if jd_signals.hard_tools else "None identified"
        )
        domain_terms_str = (
            ", ".join(jd_signals.domain_terms[:8]) if jd_signals.domain_terms else "None identified"
        )

        # Format metrics
        metrics_str = (
            "\n".join([f"- {k}: {v}" for k, v in metrics.items()]) if metrics else "None provided"
        )

        # Build prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            bullet=bullet,
            role=role,
            soft_skills=soft_skills_str,
            hard_tools=hard_tools_str,
            domain_terms=domain_terms_str,
            metrics=metrics_str,
            context=extra_context or "None",
            num_variants=num_variants,
            max_words=max_words,
        )

        # Get LLM response
        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,  # Slightly higher for variety
        )

        # Parse variants
        variants = []
        for variant_data in response.get("variants", []):
            variants.append(
                RewriteVariant(
                    text=variant_data.get("text", ""), rationale=variant_data.get("rationale", "")
                )
            )

        return variants

    def rewrite_all(
        self,
        bullets: list[str],
        role: str,
        jd_signals: JDSignals,
        bullet_metrics: list[dict[str, Any]],
        extra_context: str = "",
        max_words: int = 30,
        num_variants: int = 2,
    ) -> dict[str, list[RewriteVariant]]:
        """
        Rewrite all bullets with per-bullet metrics.
        
        OPTIMIZATION: Batch process bullets to reduce API calls.

        Args:
            bullets: List of original bullets
            role: Target role
            jd_signals: Extracted JD signals
            bullet_metrics: List of metrics dicts, one per bullet
            extra_context: Additional context
            max_words: Maximum words per variant
            num_variants: Number of variants to generate

        Returns:
            Dict mapping original bullet to variants
        """
        # OPTIMIZATION: Batch process up to 5 bullets per API call
        batch_size = 5
        results = {}
        
        for i in range(0, len(bullets), batch_size):
            batch_bullets = bullets[i:i + batch_size]
            batch_metrics = bullet_metrics[i:i + batch_size]
            
            if len(batch_bullets) == 1:
                # Single bullet - use original method
                variants = self.rewrite_bullet(
                    bullet=batch_bullets[0],
                    role=role,
                    jd_signals=jd_signals,
                    metrics=batch_metrics[0],
                    extra_context=extra_context,
                    max_words=max_words,
                    num_variants=num_variants,
                )
                results[batch_bullets[0]] = variants
            else:
                # Multiple bullets - batch process
                batch_results = self._rewrite_batch(
                    bullets=batch_bullets,
                    role=role,
                    jd_signals=jd_signals,
                    bullet_metrics=batch_metrics,
                    extra_context=extra_context,
                    max_words=max_words,
                    num_variants=num_variants,
                )
                results.update(batch_results)
        
        return results

    def _rewrite_batch(
        self,
        bullets: list[str],
        role: str,
        jd_signals: JDSignals,
        bullet_metrics: list[dict[str, Any]],
        extra_context: str = "",
        max_words: int = 30,
        num_variants: int = 2,
    ) -> dict[str, list[RewriteVariant]]:
        """
        Batch rewrite multiple bullets in a single API call.
        
        Args:
            bullets: List of bullets to rewrite
            role: Target role
            jd_signals: Extracted JD signals
            bullet_metrics: List of metrics dicts, one per bullet
            extra_context: Additional context
            max_words: Maximum words per variant
            num_variants: Number of variants to generate

        Returns:
            Dict mapping original bullet to variants
        """
        # Format categorized keywords
        soft_skills_str = (
            ", ".join(jd_signals.soft_skills[:8]) if jd_signals.soft_skills else "None identified"
        )
        hard_tools_str = (
            ", ".join(jd_signals.hard_tools[:8]) if jd_signals.hard_tools else "None identified"
        )
        domain_terms_str = (
            ", ".join(jd_signals.domain_terms[:8]) if jd_signals.domain_terms else "None identified"
        )

        # Build batch prompt
        bullets_text = "\n\n".join([
            f"Bullet {i+1}: {bullet}\nMetrics: {metrics if metrics else 'None provided'}"
            for i, (bullet, metrics) in enumerate(zip(bullets, bullet_metrics))
        ])

        batch_user_prompt = f"""Rewrite these {len(bullets)} resume bullets to align with the target job description while preserving factual accuracy.

Target Role: {role}

JD KEYWORDS (use appropriately):

✅ SOFT SKILLS (ADD if the bullet demonstrates them):
{soft_skills_str}

❌ HARD TOOLS (NEVER add unless in original bullet):
{hard_tools_str}

✅ DOMAIN TERMS (ADD ONLY if in original bullet or surrounding context):
{domain_terms_str}

Extra Context:
{extra_context or "None"}

BULLETS TO REWRITE:
{bullets_text}

REWRITING RULES:
1. SOFT SKILLS: If the work demonstrates a soft skill, weave it in naturally
2. HARD TOOLS: ONLY mention if in original bullet - adding them is fabrication
3. DOMAIN TERMS: ADD ONLY if already in original bullet or clearly implied by surrounding context

Generate {num_variants} variants per bullet (≤{max_words} words each).

Return JSON:
{{
  "results": [
    {{
      "bullet_index": 0,
      "original": "original bullet text",
      "variants": [
        {{
          "text": "...",
          "rationale": "Explain what was preserved vs. adapted"
        }}
      ]
    }},
    ...
  ]
}}
"""

        # Get LLM response
        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=batch_user_prompt,
            temperature=0.4,
        )

        # Parse results
        results = {}
        for result_data in response.get("results", []):
            bullet_index = result_data.get("bullet_index", 0)
            original_bullet = bullets[bullet_index]
            
            variants = []
            for variant_data in result_data.get("variants", []):
                variants.append(
                    RewriteVariant(
                        text=variant_data.get("text", ""),
                        rationale=variant_data.get("rationale", "")
                    )
                )
            
            results[original_bullet] = variants

        return results

    def format_skills(
        self, skills: list[str], jd_signals: JDSignals, num_variants: int = 2
    ) -> dict[str, list[RewriteVariant]]:
        """
        Light format skill bullets - keyword swap only, no full rewrite.

        Args:
            skills: List of skill bullets
            jd_signals: Extracted JD signals
            num_variants: Number of variants (usually 1-2)

        Returns:
            Dict mapping original skill to variants
        """
        results = {}

        for skill in skills:
            # Simple keyword mapping without full rewrite
            # Just swap obvious terms to match JD vocabulary
            # For now, keep it simple - just preserve the skill as-is

            # Create minimal variants (mostly just the original)
            variants = [
                RewriteVariant(
                    text=skill,  # Keep original for now
                    rationale="Skill bullet preserved with minimal formatting",
                )
            ]

            # If num_variants > 1, create a second that's the same
            if num_variants > 1:
                variants.append(RewriteVariant(text=skill, rationale="Skill bullet preserved"))

            results[skill] = variants

        return results
