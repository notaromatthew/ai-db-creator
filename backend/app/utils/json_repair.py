import json
import re
from typing import Any


def repair_and_load_json(raw: str) -> Any:
    """Attempt to parse JSON from LLM output, repairing common defects:
    - Markdown fences (```json ... ```)
    - Trailing commas before } or ]
    - Single-line and multi-line comments
    - Single quotes instead of double quotes (where safe)
    - Truncated strings, arrays, or objects
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty JSON string")

    # 1. First try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2. Extract from code block or outer braces
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if code_match:
        cand = code_match.group(1).strip()
        try:
            return json.loads(cand)
        except Exception:
            raw = cand
    else:
        first_brace = raw.find("{")
        last_brace = raw.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            cand = raw[first_brace : last_brace + 1]
            try:
                return json.loads(cand)
            except Exception:
                raw = cand
        elif first_brace != -1:
            raw = raw[first_brace:]

    # 3. Strip comments
    raw = re.sub(r"//[^\n]*\n", "\n", raw)
    raw = re.sub(r"/\*[\s\S]*?\*/", "", raw)

    # 4. Remove trailing commas
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        return json.loads(raw)
    except Exception:
        pass

    # 5. Fix truncated brackets and quotes
    in_string = False
    escape = False
    open_brackets = []

    for char in raw:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char in ("{", "["):
                open_brackets.append(char)
            elif char == "}" and open_brackets and open_brackets[-1] == "{":
                open_brackets.pop()
            elif char == "]" and open_brackets and open_brackets[-1] == "[":
                open_brackets.pop()

    repaired = raw
    if in_string:
        repaired += '"'

    for bracket in reversed(open_brackets):
        repaired = re.sub(r",\s*$", "", repaired.rstrip())
        if bracket == "{":
            repaired += "}"
        elif bracket == "[":
            repaired += "]"

    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    try:
        return json.loads(repaired)
    except Exception:
        pass

    # 6. Try replacing single quotes with double quotes
    sq_repaired = re.sub(r"'([^']*)'", r'"\1"', repaired)
    sq_repaired = re.sub(r",\s*([}\]])", r"\1", sq_repaired)
    return json.loads(sq_repaired)
