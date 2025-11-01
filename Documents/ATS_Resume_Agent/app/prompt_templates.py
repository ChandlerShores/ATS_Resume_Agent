SYSTEM_ROLE = (
    "You are \"ATS Bullet Rewriter,\" an expert language model that rewrites resume bullet "
    "points to align with a Job Description (JD) for ATS systems.\n\n"
    "Follow these rules:\n"
    "1. Output STRICT JSON per schema.\n"
    "2. Do not fabricate employers, titles, or numbers.\n"
    "3. Use strong action verbs, simple ASCII, one idea per bullet.\n"
    "4. Mirror JD keywords truthfully.\n"
    "5. Tense = params.target_tense or inferred if \"auto\".\n"
    "6. Internal step: derive a JD Signal Map (skills, tools, competencies) to guide rewrites and grading. Do NOT output this map.\n"
)


USER_INSTRUCTIONS = (
    "You will receive a job_description, resume_bullets, params, and a JSON Schema.\n"
    "Rewrite each resume bullet to better align with the job description while remaining truthful.\n"
    "- Use one clear idea per bullet.\n"
    "- Prefer present/past tense as indicated.\n"
    "- Avoid symbols or unicode outside ASCII.\n"
    "- Keep bullets concise and within the max word budget.\n"
    "- Return ONLY a JSON object that matches the provided schema. No extra text.\n"
)


from typing import Dict, List


def assemble_user_prompt(job_description: str, resume_bullets: List[str], params: Dict) -> str:
    return (
        "Inputs:\n"
        f"- job_description → {job_description}\n"
        f"- resume_bullets → {resume_bullets}\n"
        f"- params → {params}\n"
        "\nOutput Schema Keys (attach versions as provided):\n"
        "{\n"
        "  \"version\": \"string\",\n"
        "  \"prompt_version\": \"string\",\n"
        "  \"api_version\": \"string\",\n"
        "  \"schema_version\": \"string\",\n"
        "  \"request_id\": \"string\",\n"
        "  \"jd_signals\": { \"matched\": [\"string\"], \"missing_but_relevant\": [\"string\"] },\n"
        "  \"bullets\": [ { \"original\": \"string\", \"revised\": \"string\", \"word_count\": 0, \"matched_signals\": [\"string\"], \"warnings\": [\"string\"] } ],\n"
        "  \"grade\": { \"overall_score\": 0, \"letter\": \"A|B|C|D|F\", \"subscores\": { \"alignment\": 0, \"impact\": 0, \"clarity\": 0, \"brevity\": 0, \"ats_compliance\": 0 }, \"rationale\": \"string\", \"suggested_global_improvements\": [\"string\"] }\n"
        "}\n"
        "Grading Rubric Weights: Alignment 40, Impact 25, Clarity 15, Brevity 10, ATS Compliance 10.\n"
        "Warning Catalog: insufficient_quant_detail, tense_inferred, possible_scope_ambiguity, limited_jd_alignment, tool_name_normalized, overlength_trimmed.\n"
    )


REPAIR_INSTRUCTION = (
    "Your previous response did not match the required JSON schema.\n"
    "Repair-only: Fix JSON field names and types to match the schema exactly.\n"
    "Do not change any substantive content.\n"
    "Return ONLY a JSON object.\n"
)


