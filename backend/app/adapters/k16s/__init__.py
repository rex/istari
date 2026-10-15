"""HTTP adapter for the K16S exam server (verified labs)."""

from __future__ import annotations

from app.adapters.k16s.client import K16sClient, K16sTimeouts

__all__ = ["K16sClient", "K16sTimeouts"]
