from __future__ import annotations


def normalize_line_items(raw_items: list[str] | None) -> list[str]:
    if not raw_items:
        return []
    return [item.strip() for item in raw_items if item and item.strip()]
