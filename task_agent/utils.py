from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def safe_json_loads(text: str) -> Any:
    """Best-effort JSON extraction for LLM responses."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    preview = cleaned[:500]
    raise ValueError(f"Could not parse JSON from model output: {preview}")
