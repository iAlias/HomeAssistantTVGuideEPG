"""Pure logic for matching favorite programs against a parsed schedule."""

from __future__ import annotations

from typing import Dict, List, Optional


def parse_favorites(raw: str) -> List[str]:
    """Split a comma-separated string of favorite titles into a clean list."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def matching_channels(
    schedule: Dict[str, Dict[str, Optional[str]]], favorite: str
) -> Dict[str, str]:
    """Return {channel: title} for programs whose title contains ``favorite``.

    Matching is a case-insensitive substring check, so a favorite like
    "Report" also matches a title such as "Report - Speciale".
    """
    needle = favorite.casefold()
    return {
        channel: info["titolo"]
        for channel, info in schedule.items()
        if needle in (info.get("titolo") or "").casefold()
    }
