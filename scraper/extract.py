from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

MONTHS_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

DATE_TOKEN = re.compile(
    r"(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}\s+a\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?)"
)


@dataclass
class TimelineEntry:
    label: str
    date: str
    is_range: bool = False


@dataclass
class ListingItem:
    title: str
    url: str
    excerpt: str
    image_url: str | None
    published_label: str
    categories: list[str]


@dataclass
class ArticleData:
    title: str
    url: str
    published_iso: str | None
    timeline: list[TimelineEntry] = field(default_factory=list)
    official_url: str | None = None
    warning_note: str | None = None


def _classes_for_article(article: Tag) -> list[str]:
    cls = article.get("class") or []
    return [c for c in cls if c.startswith("category-")]


def parse_listing(html: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[ListingItem] = []
    for article in soup.select("article.entry-preview"):
        title_link = article.select_one("h2.entry-title a")
        if not title_link:
            continue
        url = title_link.get("href", "").strip()
        title = title_link.get_text(strip=True)
        excerpt_el = article.select_one("div.entry-excerpt")
        excerpt = excerpt_el.get_text(" ", strip=True) if excerpt_el else ""
        img = article.select_one("img[data-lazy-src], img[src]")
        image_url = None
        if img:
            image_url = img.get("data-lazy-src") or img.get("src")
            if image_url and image_url.startswith("data:"):
                image_url = img.get("data-lazy-src")
        date_el = article.select_one("li.meta-date")
        date_label = date_el.get_text(" ", strip=True) if date_el else ""
        items.append(
            ListingItem(
                title=title,
                url=url,
                excerpt=excerpt,
                image_url=image_url,
                published_label=date_label,
                categories=_classes_for_article(article),
            )
        )
    return items


# Domínios que NUNCA são o link oficial do processo
_SKIP_NETLOC = {
    "facebook.com", "t.me", "twitter.com", "x.com", "linkedin.com",
    "instagram.com", "youtube.com", "wa.me", "whatsapp.com",
}
_SKIP_NETLOC_PARTIAL = [
    "estrategia",   # todos os domínios próprios
    "google.com",
    "gravatar.com",
    "wp.com",
]
_SKIP_PATH_FRAGMENTS = [
    "politica-de-privacidade", "politica_de_privacidade",
    "unsubscribe", "sharer", "shareArticle", "share?",
]


def _is_external_link(href: str, *, host: str = "med.estrategia.com") -> bool:
    if not href or href.startswith("#"):
        return False
    parsed = urlparse(href)
    if not parsed.netloc:
        return False
    return host not in parsed.netloc


def _is_official_candidate(href: str) -> bool:
    """Retorna True se o link parece ser o portal oficial do processo seletivo."""
    if not href or href.startswith(("#", "mailto:", "tel:")):
        return False
    parsed = urlparse(href)
    if not parsed.scheme or not parsed.netloc:
        return False
    netloc = parsed.netloc.lower()
    # Rejeita domínios próprios / redes sociais
    for skip in _SKIP_NETLOC:
        if skip in netloc:
            return False
    for partial in _SKIP_NETLOC_PARTIAL:
        if partial in netloc:
            return False
    # Rejeita padrões de path suspeitos
    full = href.lower()
    for frag in _SKIP_PATH_FRAGMENTS:
        if frag in full:
            return False
    return True


def _parse_ptbr_date_label(label: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})", label, flags=re.I)
    if not m:
        return None
    day, month_name, year = m.groups()
    month = MONTHS_PT.get(month_name.lower())
    if not month:
        return None
    try:
        return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _normalize_label(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.rstrip(":").strip()
    return text


def _extract_timeline_from_table(table: Tag) -> list[TimelineEntry]:
    out: list[TimelineEntry] = []
    for row in table.select("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = _normalize_label(cells[0].get_text(" ", strip=True))
        value = _normalize_label(cells[1].get_text(" ", strip=True))
        if not label or not value:
            continue
        if not DATE_TOKEN.search(value):
            continue
        out.append(
            TimelineEntry(
                label=label,
                date=value,
                is_range=" a " in value,
            )
        )
    return out


def _extract_timeline_from_list(items: Iterable[Tag]) -> list[TimelineEntry]:
    out: list[TimelineEntry] = []
    for li in items:
        text = li.get_text(" ", strip=True)
        if ":" not in text:
            continue
        label, _, rest = text.partition(":")
        rest = rest.strip().rstrip(";.")
        if not DATE_TOKEN.search(rest):
            continue
        out.append(
            TimelineEntry(
                label=_normalize_label(label),
                date=rest.strip(),
                is_range=" a " in rest,
            )
        )
    return out


def _find_warning_block(soup: BeautifulSoup) -> Tag | None:
    for p in soup.select("p.wp-block-verse"):
        return p
    for p in soup.select("p"):
        text = p.get_text(" ", strip=True)
        if len(text) > 600:
            continue
        lowered = text.lower()
        if "⚠" in text or lowered.startswith("atenção"):
            if "recomenda" in lowered or "página oficial" in lowered or "candidato" in lowered:
                return p
    return None


def parse_article(html: str, url: str) -> ArticleData:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.entry-title, h1")
    title = title_el.get_text(" ", strip=True) if title_el else url

    published_iso: str | None = None
    meta_date = soup.select_one("li.meta-date, .meta-date, time")
    if meta_date:
        if meta_date.has_attr("datetime"):
            published_iso = meta_date["datetime"][:10]
        else:
            published_iso = _parse_ptbr_date_label(meta_date.get_text(" ", strip=True))
    if not published_iso:
        og = soup.find("meta", attrs={"property": "article:published_time"})
        if og and og.get("content"):
            published_iso = og["content"][:10]

    content = soup.select_one("div.entry-content") or soup
    timeline: list[TimelineEntry] = []
    for table in content.select("table"):
        candidate = _extract_timeline_from_table(table)
        if len(candidate) >= 3:
            timeline = candidate
            break
    if not timeline:
        for ul in content.select("ul"):
            candidate = _extract_timeline_from_list(ul.find_all("li", recursive=False))
            if len(candidate) >= 3:
                timeline = candidate
                break

    warning_note: str | None = None
    official_url: str | None = None
    warning = _find_warning_block(soup)
    if warning:
        warning_note = warning.get_text(" ", strip=True)
        warning_note = re.sub(r"^[⚠\s​️]+", "", warning_note).strip()
        for a in warning.find_all("a"):
            href = a.get("href", "")
            if _is_official_candidate(href):
                official_url = href
                break

    if not official_url:
        # Procura em todo o conteúdo: prioriza links com âncora indicativa de inscrição/edital
        priority_anchors = re.compile(
            r"inscri[çc][aã]|acesse|confira|edital|processo|portal|candidato",
            re.I,
        )
        fallback_pdf: str | None = None
        for a in content.select("a[href]"):
            href = a.get("href", "")
            if not _is_official_candidate(href):
                continue
            if "wp-content/uploads" in href:
                # PDFs são candidatos de última instância
                if not fallback_pdf and href.lower().endswith(".pdf"):
                    fallback_pdf = href
                continue
            anchor_text = a.get_text(strip=True)
            if priority_anchors.search(anchor_text) or priority_anchors.search(href):
                official_url = href
                break
        # Se nenhum link prioritário, tenta o primeiro candidato externo genérico
        if not official_url:
            for a in content.select("a[href]"):
                href = a.get("href", "")
                if _is_official_candidate(href) and "wp-content/uploads" not in href:
                    official_url = href
                    break
        # Último recurso: PDF
        if not official_url and fallback_pdf:
            official_url = fallback_pdf

    return ArticleData(
        title=title,
        url=url,
        published_iso=published_iso,
        timeline=timeline,
        official_url=official_url,
        warning_note=warning_note,
    )


# ---------------------------------------------------------------------------
# RSS feed parser — fonte suplementar sem cache de busca
# ---------------------------------------------------------------------------

def _rss_categories(item: ET.Element) -> list[str]:
    """Converte tags <category> do RSS nos slugs CSS usados pelo HTML listing."""
    cats: list[str] = []
    for cat_el in item.findall("category"):
        name = (cat_el.text or "").lower()
        if "concurs" in name:
            cats.append("category-concursos")
        elif "prova" in name or "título" in name or "titulo" in name:
            cats.append("category-provas-de-titulo-noticias")
        else:
            cats.append("category-noticias")
    return cats or ["category-noticias"]


def parse_rss_listing(xml: str) -> list[ListingItem]:
    """Parseia o feed RSS do portal e retorna ListingItems compatíveis com parse_listing."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    items: list[ListingItem] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        desc_raw = item.findtext("description") or ""
        excerpt = BeautifulSoup(desc_raw, "html.parser").get_text(" ", strip=True)[:400]
        categories = _rss_categories(item)
        items.append(
            ListingItem(
                title=title,
                url=link,
                excerpt=excerpt,
                image_url=None,
                published_label="",
                categories=categories,
            )
        )
    return items
