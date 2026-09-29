from __future__ import annotations

import argparse
import sys

from . import classify, fetch, pdf_fee, store
from .extract import ListingItem, parse_article, parse_listing, parse_rss_listing
from .identify import detect_exam_year, detect_source
from .rewrite import rewrite_title

LISTING_URL = "https://med.estrategia.com/portal/?s=edital"
RSS_URL = "https://med.estrategia.com/portal/category/noticias/feed/"
RSS_PAGES = 2  # 15 itens por página; 2 páginas cobrem fins de semana e dias cheios


def _fetch_sources(no_cache: bool) -> tuple[list[ListingItem], list[ListingItem]]:
    # Fonte 1 — busca HTML (cobertura ampla, mas sujeita a cache de horas no servidor)
    print(f"[fetch] listagem: {LISTING_URL}")
    listing_html = fetch.fetch(LISTING_URL, use_cache=not no_cache)
    items_search = parse_listing(listing_html)

    # Fonte 2 — RSS feed (sem cache, detecta artigos recém-publicados imediatamente)
    items_rss: list[ListingItem] = []
    for page in range(1, RSS_PAGES + 1):
        url = RSS_URL if page == 1 else f"{RSS_URL}?paged={page}"
        print(f"[fetch] feed RSS: {url}")
        try:
            items_rss += parse_rss_listing(fetch.fetch(url, use_cache=not no_cache))
        except Exception as exc:  # noqa: BLE001
            print(f"    RSS fetch falhou: {exc!r} — continuando sem esta página")
    return items_search, items_rss


def run(
    *, no_cache: bool = False, limit: int | None = None, urls: list[str] | None = None
) -> int:
    # --url: processa só as URLs informadas como edital novo (recupera artigos
    # que saíram da janela da busca/RSS). Não lê a listagem.
    forced_urls = set(urls or [])
    if forced_urls:
        items_search = [
            ListingItem(title=u, url=u, excerpt="", image_url=None, published_label="", categories=[])
            for u in urls
        ]
        items_rss: list[ListingItem] = []
    else:
        items_search, items_rss = _fetch_sources(no_cache)

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
        if item.url in forced_urls:
            result = classify.Classification("edital_launch", "URL informada manualmente (--url)")
        else:
            result = classify.classify(
                title=item.title,
                excerpt=item.excerpt,
                categories=item.categories,
            )
        # "skip" com título de seleção e fora do banco vira candidato: decide pela
        # evidência na página (abaixo). Concursos nunca são candidatos.
        candidate = (
            result.kind == "skip"
            and classify.is_candidate(item.title)
            and store.slug_from_url(item.url) not in db
        )
        if result.kind == "concurso" or (result.kind == "skip" and not candidate):
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

        print(f"  [{'candidato' if candidate else result.kind}] {item.title[:80]}")
        try:
            article_html = fetch.fetch(item.url, use_cache=not no_cache)
        except Exception as exc:  # noqa: BLE001
            print(f"    fetch falhou: {exc!r}")
            continue
        article = parse_article(article_html, item.url)

        if candidate:
            if article.edital_pdf_count >= 1 and len(article.timeline) >= 3:
                result = classify.Classification(
                    "edital_launch", "evidência na página: botão de edital + cronograma"
                )
                print(f"    aceito por evidência ({article.edital_pdf_count} edital(is), {len(article.timeline)} datas)")
            else:
                skipped += 1
                print("    [skip-evidência] sem botão de edital com PDF ou sem cronograma")
                continue

        if not article.timeline:
            print("    sem timeline extraível — aceito sem cronograma")

        # Taxa ausente no artigo → tenta o PDF do edital. Só para editais novos no
        # banco: não rebaixa PDFs a cada execução nem mexe em registros já existentes.
        if (
            result.kind != "update"
            and not article.fee
            and article.edital_pdf_url
            and store.slug_from_url(item.url) not in db
        ):
            article.fee, reason = pdf_fee.fee_from_pdf(article.edital_pdf_url)
            print(f"    taxa via PDF: {article.fee or 'Confirmar'} ({reason})")

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
    parser.add_argument(
        "--url", action="append", dest="urls", metavar="URL",
        help="processa esta URL como edital novo (repetível); ignora a listagem",
    )
    args = parser.parse_args()
    sys.exit(run(no_cache=args.no_cache, limit=args.limit, urls=args.urls))


if __name__ == "__main__":
    main()
