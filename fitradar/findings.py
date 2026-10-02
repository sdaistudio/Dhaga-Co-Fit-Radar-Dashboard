"""Steps 6 and 7: write each finding (strong model), then evaluate it (code + fast model).

The code check is deliberately strict: every number that appears in the finding must be a number
that was in the evidence. A model can phrase; it cannot invent a figure.
"""
import re
from .schemas import Finding

NUMBER = re.compile(r"\d+(?:\.\d+)?")


def allowed_numbers(evidence: dict) -> set[str]:
    allowed = set()

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            allowed.add(str(value)); allowed.add(str(int(value))) if float(value).is_integer() else None
        elif isinstance(value, str):
            allowed.update(NUMBER.findall(value))
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                walk(v)

    walk(evidence)
    allowed.update({"1", "2", "30", "100"})   # "one size", "two weeks", the 30-return rule, per cent
    return allowed


def code_check(finding: Finding, evidence: dict) -> list[str]:
    """Returns the list of problems. Empty means every figure traces to the data."""
    allowed = allowed_numbers(evidence)
    text = f"{finding.headline} {finding.evidence} {finding.suggested_fix}"
    problems = []
    for n in NUMBER.findall(text):
        plain = n.rstrip("0").rstrip(".") if "." in n else n
        if n not in allowed and plain not in allowed:
            problems.append(f"The figure {n} is not in the data.")
    if evidence["vendor_id"] not in text:
        problems.append("The finding does not name the vendor.")
    return problems
