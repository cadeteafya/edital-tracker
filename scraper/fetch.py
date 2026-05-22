from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional

import httpx

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
CACHE_TTL_SECONDS = 60 * 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 EditalTracker/0.2"
)


def _cache_path(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{digest}.html"


def fetch(url: str, *, use_cache: bool = True) -> str:
    path = _cache_path(url)
    if use_cache and path.exists():
        age = time.time() - path.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return path.read_text(encoding="utf-8", errors="replace")
    with httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.text
    path.write_text(text, encoding="utf-8")
    return text
