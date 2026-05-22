import Link from "next/link";

type Props = {
  page: number;
  totalPages: number;
  query?: string;
};

function buildHref(page: number, query?: string) {
  const p = new URLSearchParams();
  if (query?.trim()) p.set("q", query.trim());
  if (page > 1) p.set("page", String(page));
  const qs = p.toString();
  return qs ? `/?${qs}` : "/";
}

export function Pagination({ page, totalPages, query }: Props) {
  if (totalPages <= 1) return null;

  // janela de páginas: mostra no máximo 5 números, centrada na página atual
  const WINDOW = 5;
  const half = Math.floor(WINDOW / 2);
  let start = Math.max(1, page - half);
  let end = Math.min(totalPages, start + WINDOW - 1);
  if (end - start + 1 < WINDOW) start = Math.max(1, end - WINDOW + 1);

  const pages = Array.from({ length: end - start + 1 }, (_, i) => start + i);

  const linkBase =
    "inline-flex items-center justify-center size-9 rounded-lg text-sm font-medium transition";
  const activeClass =
    "bg-[var(--foreground)] text-[var(--background)]";
  const idleClass =
    "border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-muted)]";
  const disabledClass =
    "border border-[var(--border)] text-[var(--muted)] pointer-events-none opacity-40";

  return (
    <nav
      aria-label="Paginação"
      className="flex items-center justify-center gap-1.5 py-10"
    >
      {/* Anterior */}
      {page > 1 ? (
        <Link href={buildHref(page - 1, query)} className={`${linkBase} ${idleClass}`} aria-label="Página anterior">
          <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </Link>
      ) : (
        <span className={`${linkBase} ${disabledClass}`} aria-disabled="true">
          <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </span>
      )}

      {/* Reticências no início */}
      {start > 1 && (
        <>
          <Link href={buildHref(1, query)} className={`${linkBase} ${idleClass}`}>1</Link>
          {start > 2 && <span className={`${linkBase} ${disabledClass}`}>…</span>}
        </>
      )}

      {/* Números */}
      {pages.map((p) => (
        <Link
          key={p}
          href={buildHref(p, query)}
          aria-current={p === page ? "page" : undefined}
          className={`${linkBase} ${p === page ? activeClass : idleClass}`}
        >
          {p}
        </Link>
      ))}

      {/* Reticências no fim */}
      {end < totalPages && (
        <>
          {end < totalPages - 1 && <span className={`${linkBase} ${disabledClass}`}>…</span>}
          <Link href={buildHref(totalPages, query)} className={`${linkBase} ${idleClass}`}>{totalPages}</Link>
        </>
      )}

      {/* Próxima */}
      {page < totalPages ? (
        <Link href={buildHref(page + 1, query)} className={`${linkBase} ${idleClass}`} aria-label="Próxima página">
          <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </Link>
      ) : (
        <span className={`${linkBase} ${disabledClass}`} aria-disabled="true">
          <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </span>
      )}
    </nav>
  );
}
