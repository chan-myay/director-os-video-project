from __future__ import annotations

import json
from typing import Iterable


def sse_events(events: Iterable[dict]) -> Iterable[str]:
    for event in events:
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
