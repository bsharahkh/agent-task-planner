from __future__ import annotations

import json
import time
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

T = TypeVar("T")


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


def retry(operation: Callable[[], T], *, attempts: int, delay_seconds: float) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds)

    assert last_error is not None
    raise last_error
