"""Shared recommendation types used by SimFix."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """A safe recommendation for system or vendor dependency guidance."""

    category: str
    title: str
    status: str
    reason: str
    suggestion: str
