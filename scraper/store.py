from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .extract import ArticleData, TimelineEntry

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "editals.json"


@dataclass
class Source:
    name: str
    shortName: str
    accentColor: str


@dataclass
class Edital:
    id: str
    source: Source
    originalTitle: str
    rewrittenTitle: str
    examYear: int
    originalUrl: str
    officialUrl: str
    scrapedAt: str          # ISO — gravado uma vez na primeira inserção, nunca sobrescrito
    publishedAt: str
    updatedAt: str
    timeline: list[dict[str, Any]]
    warningNote: str | None = None
    revisions: list[dict[str, Any]] = field(default_factory=list)


_PALETTE = [
    "#0d9488", "#0ea5e9", "#dc2626", "#7c3aed", "#f59e0b",
    "#10b981", "#ef4444", "#3b82f6", "#a855f7", "#ec4899",
    "#22c55e", "#f97316", "#14b8a6",
]


def color_for(short_name: str) -> str:
    h = int(hashlib.sha1(short_name.lower().encode("utf-8")).hexdigest(), 16)
    return _PALETTE[h % len(_PALETTE)]


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").split("/")[-1]
    return path or hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def load() -> dict[str, dict[str, Any]]:
    if not DATA_PATH.exists():
        return {}
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in raw.get("editals", [])}


def save(records: dict[str, dict[str, Any]]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lastSyncedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "editals": sorted(
            records.values(),
            key=lambda r: r.get("updatedAt", ""),
            reverse=True,
        ),
    }
    DATA_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _serialize_timeline(timeline: list[TimelineEntry]) -> list[dict[str, Any]]:
    return [
        {"label": e.label, "date": e.date, "isRange": e.is_range}
        for e in timeline
    ]


def build_record(
    article: ArticleData,
    *,
    rewritten_title: str,
    source: Source,
    exam_year: int,
    revision_of: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).date().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec = Edital(
        id=slug_from_url(article.url),
        source=source,
        originalTitle=article.title,
        rewrittenTitle=rewritten_title,
        examYear=exam_year,
        originalUrl=article.url,
        officialUrl=article.official_url or "",
        scrapedAt=now_iso,      # gravado aqui, preservado pelo merge()
        publishedAt=article.published_iso or now,
        updatedAt=article.published_iso or now,
        timeline=_serialize_timeline(article.timeline),
        warningNote=article.warning_note,
    )
    payload = asdict(rec)
    if revision_of:
        payload["revisionOf"] = revision_of
    return payload


def merge(
    existing: dict[str, dict[str, Any]],
    incoming: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rec_id = incoming["id"]
    if rec_id not in existing:
        existing[rec_id] = incoming
        return existing
    prior = existing[rec_id]
    revisions = prior.get("revisions") or []
    if prior.get("timeline") != incoming.get("timeline") or prior.get("warningNote") != incoming.get("warningNote"):
        revisions.append(
            {
                "capturedAt": prior.get("updatedAt"),
                "timeline": prior.get("timeline"),
                "warningNote": prior.get("warningNote"),
            }
        )
    merged = {**prior, **incoming}
    merged["revisions"] = revisions
    # Campos imutáveis: preserva sempre o valor original
    if prior.get("publishedAt") and not incoming.get("publishedAt"):
        merged["publishedAt"] = prior["publishedAt"]
    if prior.get("scrapedAt"):
        merged["scrapedAt"] = prior["scrapedAt"]  # nunca sobrescreve
    existing[rec_id] = merged
    return existing


def apply_revision(
    existing: dict[str, dict[str, Any]],
    parent_url: str,
    revision_article: ArticleData,
) -> bool:
    parent_id = slug_from_url(parent_url)
    if parent_id not in existing:
        return False
    parent = existing[parent_id]
    revisions = parent.get("revisions") or []
    revisions.append(
        {
            "capturedAt": revision_article.published_iso,
            "source": "retificação",
            "url": revision_article.url,
            "title": revision_article.title,
            "timeline": _serialize_timeline(revision_article.timeline),
            "warningNote": revision_article.warning_note,
        }
    )
    parent["revisions"] = revisions
    if revision_article.timeline:
        parent["timeline"] = _serialize_timeline(revision_article.timeline)
    if revision_article.warning_note:
        parent["warningNote"] = revision_article.warning_note
    if revision_article.official_url:
        parent["officialUrl"] = revision_article.official_url
    parent["updatedAt"] = (revision_article.published_iso
                          or datetime.now(timezone.utc).date().isoformat())
    return True
