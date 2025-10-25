"""Fused processor for batch rewrite + score operations in a single LLM call."""


from ops.llm_client import get_llm_client
from schemas.models import BulletDiff, BulletResult, BulletScores, JDSignals, JobSettings

SYSTEM_PROMPT = """You are an expert resume editor. Rewrite bullets and score them in one pass.

Your task is to:
1. Rewrite each bullet to be ATS-friendly, impact-focused, and aligned to the job description
2. Score each rewritten bullet on relevance, impact, and clarity
3. Provide brief rationale for changes

Focus on:
- Using active voice and strong action verbs
- Incorporating relevant keywords from the JD
- Quantifying impact where possible
- Maintaining factual accuracy
- Improving clarity and conciseness"""


USER_PROMPT_TEMPLATE = """Process these bullets for the role: {role}

JD Keywords: {top_terms}
Soft Skills: {soft_skills}
Hard Tools: {hard_tools}
Domain Terms: {domain_terms}

Writing Guidelines:
- Tone: {tone}
- Max words per bullet: {max_words}
- Use active voice and strong action verbs
- Incorporate relevant JD keywords naturally
- Quantify impact when possible
- Maintain factual accuracy

Bullets to process:
{bullets_text}

For each bullet, return:
{{
  "results": [
    {{
      "bullet_index": 0,
      "original": "original bullet text",
      "revised": "rewritten bullet text",
      "scores": {{
        "relevance": 85,
        "impact": 78,
        "clarity": 92
      }},
      "rationale": "Brief explanation of key changes made"
    }},
    ...
  ]
}}

Score each bullet on:
- relevance (0-100): How well it aligns with JD keywords/requirements
- impact (0-100): How impactful the outcomes/results are
- clarity (0-100): How clear and concise the writing is"""


class FusedProcessor:
    """Agent for batch processing bullets with rewrite + score in one LLM call."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
    
    def process_batch(
        self, 
        bullets: list[str], 
        role: str, 
        jd_signals: JDSignals, 
        settings: JobSettings
    ) -> list[BulletResult]:
        """
        Process multiple bullets in a single batch LLM call.
        
        Args:
            bullets: List of original bullet texts
            role: Target role/position
            jd_signals: Extracted JD signals
            settings: Job settings (tone, max_words, etc.)
            
        Returns:
            List of BulletResult objects
        """
        from ops.logging import logger
        
        if not bullets:
            return []
        
        # Prepare bullets text
        bullets_text = "\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(bullets)])
        
        # Prepare JD signals for prompt
        top_terms = ", ".join(jd_signals.top_terms[:15])  # Limit to top 15
        soft_skills = ", ".join(jd_signals.soft_skills[:10])
        hard_tools = ", ".join(jd_signals.hard_tools[:10])
        domain_terms = ", ".join(jd_signals.domain_terms[:10])
        
        # Create user prompt
        user_prompt = USER_PROMPT_TEMPLATE.format(
            role=role,
            top_terms=top_terms,
            soft_skills=soft_skills,
            hard_tools=hard_tools,
            domain_terms=domain_terms,
            tone=settings.tone,
            max_words=settings.max_len,
            bullets_text=bullets_text
        )
        
        try:
            # Call LLM for batch processing
            response = self.llm_client.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3  # Lower temperature for more consistent results
            )
            
            # Parse results
            results = []
            llm_results = response.get("results", [])
            
            for i, bullet in enumerate(bullets):
                # Find corresponding LLM result
                llm_result = None
                for result in llm_results:
                    if result.get("bullet_index") == i:
                        llm_result = result
                        break
                
                if llm_result:
                    # Create BulletResult from LLM response
                    scores = BulletScores(
                        relevance=llm_result.get("scores", {}).get("relevance", 50),
                        impact=llm_result.get("scores", {}).get("impact", 50),
                        clarity=llm_result.get("scores", {}).get("clarity", 50)
                    )
                    
                    bullet_result = BulletResult(
                        original=bullet,
                        revised=[llm_result.get("revised", bullet)],
                        scores=scores,
                        notes=llm_result.get("rationale", "No rationale provided"),
                        diff=BulletDiff(removed=[], added_terms=[])  # Will be computed later
                    )
                else:
                    # Fallback: create minimal result if LLM didn't process this bullet
                    scores = BulletScores(relevance=50, impact=50, clarity=50)
                    bullet_result = BulletResult(
                        original=bullet,
                        revised=[bullet],  # Keep original
                        scores=scores,
                        notes="Failed to process in batch",
                        diff=BulletDiff(removed=[], added_terms=[])
                    )
                
                results.append(bullet_result)
            
            logger.info(
                stage="fused_processor",
                msg=f"Batch processed {len(bullets)} bullets",
                bullets_processed=len(results),
                llm_results_count=len(llm_results)
            )
            
            return results
            
        except Exception as e:
            logger.warn(
                stage="fused_processor",
                msg=f"Batch processing failed: {e}",
                error=str(e)
            )
            
            # Fallback: create minimal results for all bullets
            fallback_results = []
            for bullet in bullets:
                scores = BulletScores(relevance=50, impact=50, clarity=50)
                fallback_results.append(BulletResult(
                    original=bullet,
                    revised=[bullet],  # Keep original
                    scores=scores,
                    notes=f"Batch processing failed: {str(e)}",
                    diff=BulletDiff(removed=[], added_terms=[])
                ))
            
            return fallback_results
