from typing import Dict, List


def approx_token_count(text: str) -> int:
    # Rough heuristic: 1 token ~= 4 chars in English text
    return max(1, len(text) // 4)


def compute_input_metrics(job_description: str, resume_bullets: List[str]) -> Dict[str, int]:
    jd_chars = len(job_description)
    bullets_chars = sum(len(b) for b in resume_bullets)
    total_chars = jd_chars + bullets_chars
    return {
        "jd_chars": jd_chars,
        "bullets_chars": bullets_chars,
        "total_chars": total_chars,
        "estimated_tokens": approx_token_count(job_description) + sum(approx_token_count(b) for b in resume_bullets),
    }


