"""SCORER agent: Scores bullet variants on relevance, impact, and clarity."""

from ops.llm_client import get_llm_client
from schemas.models import BulletScores, Coverage, JDSignals

SYSTEM_PROMPT = """You are an expert at evaluating resume bullets for ATS compatibility and impact.

Score bullets on three dimensions (0-100):

1. RELEVANCE: How well the bullet aligns with job description priorities
   - 90-100: Directly matches multiple must-have skills/competencies
   - 70-89: Matches some important JD terms
   - 50-69: Tangentially related
   - Below 50: Poor alignment

2. IMPACT: Strength of outcomes, scope, and efficiency gains
   - 90-100: Clear quantified outcome with business impact
   - 70-89: Qualitative impact with scope/scale
   - 50-69: Action described but outcome unclear
   - Below 50: No clear value demonstrated

3. CLARITY: Brevity, concreteness, and ease of understanding
   - 90-100: Crisp, concrete, no filler, perfect grammar
   - 70-89: Clear but could be tighter
   - 50-69: Somewhat vague or wordy
   - Below 50: Confusing or grammatically poor"""


USER_PROMPT_TEMPLATE = """Score this revised resume bullet.

Original: {original}
Revised: {revised}

Target Role: {role}
Key JD Terms: {jd_terms}

Return JSON:
{{
  "relevance": <0-100>,
  "impact": <0-100>,
  "clarity": <0-100>,
  "explanation": "1-2 sentences explaining the scores"
}}"""


class Scorer:
    """Agent for scoring bullet variants."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()

    def score_variant(
        self, original: str, revised: str, role: str, jd_signals: JDSignals
    ) -> tuple[BulletScores, str]:
        """
        Score a single variant.

        Args:
            original: Original bullet
            revised: Revised bullet
            role: Target role
            jd_signals: JD signals for alignment checking

        Returns:
            tuple[BulletScores, str]: Scores and explanation
        """
        jd_terms_str = ", ".join(jd_signals.top_terms[:10])

        user_prompt = USER_PROMPT_TEMPLATE.format(
            original=original, revised=revised, role=role, jd_terms=jd_terms_str
        )

        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,  # Lower for consistent scoring
        )

        scores = BulletScores(
            relevance=response.get("relevance", 0),
            impact=response.get("impact", 0),
            clarity=response.get("clarity", 0),
        )

        explanation = response.get("explanation", "")

        return scores, explanation

    def score_batch(
        self, bullets_data: list[tuple[str, str]], role: str, jd_signals: JDSignals
    ) -> list[tuple[BulletScores, str]]:
        """
        Score multiple bullet variants in a single API call.
        
        Args:
            bullets_data: List of (original, revised) tuples
            role: Target role
            jd_signals: JD signals for alignment checking

        Returns:
            List of (scores, explanation) tuples
        """
        jd_terms_str = ", ".join(jd_signals.top_terms[:10])
        
        bullets_text = "\n\n".join([
            f"Bullet {i+1}:\nOriginal: {original}\nRevised: {revised}"
            for i, (original, revised) in enumerate(bullets_data)
        ])

        batch_prompt = f"""Score these {len(bullets_data)} revised resume bullets.

Target Role: {role}
Key JD Terms: {jd_terms_str}

BULLETS TO SCORE:
{bullets_text}

Return JSON:
{{
  "scores": [
    {{
      "bullet_index": 0,
      "relevance": <0-100>,
      "impact": <0-100>,
      "clarity": <0-100>,
      "explanation": "1-2 sentences explaining the scores"
    }},
    ...
  ]
}}"""

        response = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=batch_prompt,
            temperature=0.2,
        )

        results = []
        for score_data in response.get("scores", []):
            bullet_index = score_data.get("bullet_index", 0)
            
            # Safety check: ensure bullet_index is within bounds
            if bullet_index >= len(bullets_data):
                continue
                
            scores = BulletScores(
                relevance=score_data.get("relevance", 0),
                impact=score_data.get("impact", 0),
                clarity=score_data.get("clarity", 0),
            )
            explanation = score_data.get("explanation", "")
            results.append((scores, explanation))

        # Fallback: if batch processing failed, process individually
        if not results:
            for original, revised in bullets_data:
                scores, explanation = self.score_variant(
                    original=original,
                    revised=revised,
                    role=role,
                    jd_signals=jd_signals,
                )
                results.append((scores, explanation))

        return results

    def compute_coverage(self, all_revised_bullets: list[str], jd_signals: JDSignals) -> Coverage:
        """
        Compute coverage of JD terms across all bullets.

        Args:
            all_revised_bullets: All revised bullets
            jd_signals: JD signals to check against

        Returns:
            Coverage: Hit and miss terms
        """
        # Combine all revised text
        combined_text = " ".join(all_revised_bullets).lower()

        hit_terms: set[str] = set()
        miss_terms: set[str] = set()

        for term in jd_signals.top_terms:
            term_lower = term.lower()

            # Check if term or its synonyms appear
            found = term_lower in combined_text

            if not found and term in jd_signals.synonyms:
                # Check synonyms
                for synonym in jd_signals.synonyms[term]:
                    if synonym.lower() in combined_text:
                        found = True
                        break

            if found:
                hit_terms.add(term)
            else:
                miss_terms.add(term)

        return Coverage(hit=sorted(list(hit_terms)), miss=sorted(list(miss_terms)))
