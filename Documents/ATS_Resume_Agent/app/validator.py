from __future__ import annotations

from typing import Dict, List

from pydantic import ValidationError

from .schemas import RewriteRequest, RewriteResponse, BulletItem, Grade, JDSignals


def _count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])


def _grade_letter(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def reconcile_bullets(
    original_bullets: List[str],
    model_bullets: List[Dict],
    max_words: int,
) -> List[BulletItem]:
    # Align counts; if too many, truncate; if too few, pad with originals
    aligned: List[Dict] = list(model_bullets[: len(original_bullets)])
    while len(aligned) < len(original_bullets):
        orig = original_bullets[len(aligned)]
        aligned.append(
            {
                "original": orig,
                "revised": orig,
                "word_count": _count_words(orig),
                "matched_signals": [],
                "warnings": ["limited_jd_alignment"],
            }
        )

    bullet_items: List[BulletItem] = []
    for i, b in enumerate(aligned):
        original = original_bullets[i]
        revised = b.get("revised") or b.get("original") or original
        warnings = list(b.get("warnings") or [])

        # Enforce single-line ASCII-like bullet and trim words
        words = revised.strip().split()
        if len(words) > max_words:
            revised = " ".join(words[:max_words])
            warnings.append("overlength_trimmed")

        word_count = _count_words(revised)

        bullet_items.append(
            BulletItem(
                original=original,
                revised=revised,
                word_count=word_count,
                matched_signals=list(b.get("matched_signals") or []),
                warnings=warnings,
            )
        )
    return bullet_items


def reconcile_grade(grade_dict: Dict) -> Grade:
    subs = grade_dict.get("subscores", {})
    total = int(subs.get("alignment", 0)) + int(subs.get("impact", 0)) + int(subs.get("clarity", 0)) + int(subs.get("brevity", 0)) + int(subs.get("ats_compliance", 0))
    if total > 100:
        total = 100
    if total < 0:
        total = 0
    letter = _grade_letter(total)
    gd = {
        "overall_score": total,
        "letter": grade_dict.get("letter", letter),
        "subscores": {
            "alignment": int(subs.get("alignment", 0)),
            "impact": int(subs.get("impact", 0)),
            "clarity": int(subs.get("clarity", 0)),
            "brevity": int(subs.get("brevity", 0)),
            "ats_compliance": int(subs.get("ats_compliance", 0)),
        },
        "rationale": grade_dict.get("rationale", ""),
        "suggested_global_improvements": list(grade_dict.get("suggested_global_improvements", [])),
    }
    # Ensure letter aligns with computed score
    gd["letter"] = _grade_letter(gd["overall_score"])
    return Grade(**gd)


def validate_and_reconcile(model_json: Dict, req: RewriteRequest) -> RewriteResponse:
    # Rebuild response fields to enforce determinism
    jd_signals_dict = model_json.get("jd_signals") or {"matched": [], "missing_but_relevant": []}

    bullets_list = model_json.get("bullets") or []
    bullets = reconcile_bullets(
        original_bullets=req.resume_bullets,
        model_bullets=bullets_list,
        max_words=req.params.max_words_per_bullet,
    )

    grade = reconcile_grade(model_json.get("grade") or {})

    final = {
        "version": model_json.get("version"),
        "prompt_version": model_json.get("prompt_version"),
        "api_version": model_json.get("api_version"),
        "schema_version": model_json.get("schema_version"),
        "request_id": req.params.request_id or model_json.get("request_id"),
        "jd_signals": JDSignals(**jd_signals_dict).model_dump(),
        "bullets": [b.model_dump() for b in bullets],
        "grade": grade.model_dump(),
    }

    try:
        return RewriteResponse(**final)
    except ValidationError as e:
        raise ValueError(f"Response validation failed: {e}")


