from typing import Dict


def recompute_overall_from_subscores(subscores: Dict[str, int]) -> int:
    total = int(subscores.get("alignment", 0)) + int(subscores.get("impact", 0)) + int(subscores.get("clarity", 0)) + int(subscores.get("brevity", 0)) + int(subscores.get("ats_compliance", 0))
    if total > 100:
        return 100
    if total < 0:
        return 0
    return total


