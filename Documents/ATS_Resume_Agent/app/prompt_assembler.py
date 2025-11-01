from typing import Any, Dict, List

from .prompt_templates import SYSTEM_ROLE, USER_INSTRUCTIONS, assemble_user_prompt
from .schemas import RewriteRequest
from .config import ATTACHED_VERSIONS


def assemble_messages(req: RewriteRequest) -> List[Dict[str, str]]:
    jd = req.job_description
    bullets = req.resume_bullets
    params = req.params.model_dump()
    versions = ATTACHED_VERSIONS

    prompt = assemble_user_prompt(
        job_description=jd,
        resume_bullets=bullets,
        params={**params, **versions},
    )
    return [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user", "content": USER_INSTRUCTIONS + "\n" + prompt},
    ]


