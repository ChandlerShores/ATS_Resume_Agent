import re
import unicodedata
from typing import List, Tuple


SMART_QUOTES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201C": '"',
    "\u201D": '"',
    "\u2013": "-",
    "\u2014": "-",
}


def _strip_emojis(text: str) -> str:
    # Remove most emoji symbols via unicode category filter
    return "".join(ch for ch in text if not unicodedata.category(ch).startswith("So"))


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = text.translate(str.maketrans(SMART_QUOTES))
    text = unicodedata.normalize("NFKC", text)
    text = _strip_emojis(text)
    # Collapse excessive newlines and spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


SECTION_HEADERS = [
    "responsibilities",
    "requirements",
    "skills",
    "what you will do",
    "what you'll do",
    "qualifications",
]


def truncate_jd_to_core_sections(jd: str) -> str:
    if not jd:
        return jd
    # Keep sentences that occur within lines after any of the section headers
    lowered = jd.lower()
    segments: List[str] = []
    for header in SECTION_HEADERS:
        idx = lowered.find(header)
        if idx != -1:
            segments.append(jd[idx: idx + 2000])  # cap per section to avoid long JDs
    if not segments:
        return jd[:4000]
    return "\n\n".join(segments)[:4000]


def normalize_resume_bullets(bullets: List[str]) -> List[str]:
    out: List[str] = []
    for b in bullets:
        nb = normalize_text(b)
        # remove leading bullet chars like -, *, •
        nb = re.sub(r"^[\-\*•\s]+", "", nb)
        out.append(nb)
    return out


def detect_current_role_hints(bullets: List[str]) -> Tuple[bool, int]:
    # Heuristic: look for present tense verbs as a rough hint
    present_markers = ["lead", "manage", "design", "build", "own", "drive"]
    hits = 0
    for b in bullets:
        for m in present_markers:
            if re.search(rf"\b{m}\b", b.lower()):
                hits += 1
                break
    return (hits > 0, hits)


