from __future__ import annotations

import argparse
import sys

from . import classify, fetch, store
from .extract import parse_article, parse_listing, parse_rss_listing
from .identify import detect_exam_year, detect_source
from .rewrite import rewrite_title

LISTING_URL = "https://med.estrategia.com/portal/?s=edital"
RSS_URL = "https://med.estrategia.com/portal/category/noticias/feed/"


def run(*, no_cache: bool = False, limit: int | None = None) -> int:
    # Fonte 1 — busca HTML (cobertura ampla, mas sujeita a cache de horas no servidor)
    print(f"[fetch] listagem: {LISTING_URL}")
    listing_html = fetch.fetch(LISTING_URL, use_cache=not no_cache)
    items_search = parse_listing(listing_html)

    # Fonte 2 — RSS feed (sem cache, detecta artigos recém-publicados imediatamente)
    print(f"[fetch] feed RSS: {RSS_URL}")
    try:
        rss_xml = fetch.fetch(RSS_URL, use_cache=not no_cache)
        items_rss = parse_rss_listing(rss_xml)
    except Exception as exc:  # noqa: BLE001
        print(f"    RSS fetch falhou: {exc!r} — continuando só com busca")
        items_rss = []

    # Mescla e deduplica por URL (busca tem precedência para preservar categories)
    seen_urls: set[str] = {i.url for i in items_search}
    items = list(items_search)
    rss_only = 0
    for rss_item in items_rss:
        if rss_item.url not in seen_urls:
            items.append(rss_item)
            seen_urls.add(rss_item.url)
            rss_only += 1
    print(f"[fetch] {len(items_search)} da busca + {rss_only} exclusivos do RSS = {len(items)} únicos")

    db = store.load()
    print(f"[store] {len(db)} editais já no banco")

    # Purga retroativa: remove registros que o classificador agora rejeita
    purged = 0
    for rec_id in list(db.keys()):
        rec = db[rec_id]
        check = classify.classify(
            title=rec.get("originalTitle", ""),
            excerpt="",
            categories=[],
        )
        if check.kind == "concurso":
            del db[rec_id]
            purged += 1
            print(f"  [purge] {rec.get('originalTitle', rec_id)[:70]} — {check.reason}")
    if purged:
        print(f"  [purge] {purged} registro(s) removido(s) do banco")

    accepted = 0
    skipped = 0
    revisions = 0

    iterable = items if limit is None else items[:limit]

    for item in iterable:
        result = classify.classify(
            title=item.title,
            excerpt=item.excerpt,
            categories=item.categories,
        )
        if result.kind == "skip" or result.kind == "concurso":
            skipped += 1
            print(f"  [skip] {item.title[:80]} — {result.reason}")
            continue

        # Artigo já no banco com cronograma e não é retificação → pula para não
        # re-disparar alertas no sistema de monitoramento externo
        if result.kind != "update":
            rec_id = store.slug_from_url(item.url)
            if rec_id in db and db[rec_id].get("timeline"):
                skipped += 1
                continue

        print(f"  [{result.kind}] {item.title[:80]}")
        try:
            article_html = fetch.fetch(item.url, use_cache=not no_cache)
        except Exception as exc:  # noqa: BLE001
            print(f"    fetch falhou: {exc!r}")
            continue
        article = parse_article(article_html, item.url)

        if not article.timeline:
            print("    sem timeline extraível — aceito sem cronograma")

        if result.kind == "update":
            applied = False
            for existing_id, existing in db.items():
                if existing.get("source", {}).get("shortName", "").lower() in article.title.lower():
                    if store.apply_revision(db, existing["originalUrl"], article):
                        applied = True
                        revisions += 1
                        print(f"    retificação aplicada ao registro {existing_id}")
                        break
            if not applied:
                print("    retificação sem registro-pai correspondente, ignorando")
                skipped += 1
            continue

        rewritten = rewrite_title(article.title)
        source_full, source_short = detect_source(article.title, article.url)
        record = store.build_record(
            article,
            rewritten_title=rewritten,
            source=store.Source(
                name=source_full,
                shortName=source_short,
                accentColor=store.color_for(source_short),
            ),
            exam_year=detect_exam_year(article.title),
        )
        store.merge(db, record)
        accepted += 1

    store.save(db)

    print()
    print(f"[done] aceitos: {accepted} · retificações: {revisions} · ignorados: {skipped}")
    print(f"[done] total no banco: {len(db)}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="scraper")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    sys.exit(run(no_cache=args.no_cache, limit=args.limit))


if __name__ == "__main__":
    main()
