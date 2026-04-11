from __future__ import annotations

import unittest

from task_agent.utils import safe_json_loads


class SafeJsonLoadsTests(unittest.TestCase):
    def test_parses_fenced_json(self) -> None:
        payload = """```json
{"action":"execute","children":[]}
```"""
        parsed = safe_json_loads(payload)
        self.assertEqual(parsed["action"], "execute")

    def test_raises_on_invalid_json(self) -> None:
        with self.assertRaises(ValueError):
            safe_json_loads("not json")


if __name__ == "__main__":
    unittest.main()
