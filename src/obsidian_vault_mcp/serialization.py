"""JSON serialization helpers for tool responses.

Frontmatter values parsed from YAML can include `datetime.date` /
`datetime.datetime` / `datetime.time` objects, which `json.dumps` does
not handle by default. Tool handlers that embed frontmatter in their
response should use `dumps()` from this module instead of `json.dumps`.
"""

import json
from datetime import date, datetime, time


def _default(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def dumps(data) -> str:
    return json.dumps(data, default=_default)
