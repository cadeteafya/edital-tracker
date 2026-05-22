import { EditalCard } from "@/components/EditalCard";
import { SiteHeader } from "@/components/SiteHeader";
import { PageIntro } from "@/components/PageIntro";
import { SearchBar } from "@/components/SearchBar";
import { Pagination } from "@/components/Pagination";
import { loadEditalsSnapshot } from "@/lib/loadEditals";
import { isNewEdital } from "@/lib/dates";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 9;

type Props = {
  searchParams: Promise<{ q?: string; page?: string }>;
};

export default async function Home({ searchParams }: Props) {
  const { q = "", page: pageStr = "1" } = await searchParams;
  const query = q.trim().toLowerCase();
  const page = Math.max(1, parseInt(pageStr, 10) || 1);

  const { editals, lastSyncedAt } = await loadEditalsSnapshot();

  // 1. Filtra por busca
  const filtered = query
    ? editals.filter(
        (e) =>
          e.source.name.toLowerCase().includes(query) ||
          e.source.shortName.toLowerCase().includes(query) ||
          e.rewrittenTitle.toLowerCase().includes(query) ||
          e.originalTitle.toLowerCase().includes(query),
      )
    : editals;

  // 2. Ordena por mais recente
  const sorted = [...filtered].sort(
    (a, b) =>
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );

  // 3. Pagina
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages);
  const pageItems = sorted.slice(
    (clampedPage - 1) * PAGE_SIZE,
    clampedPage * PAGE_SIZE,
  );

  const lastSyncedLabel = new Date(lastSyncedAt).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="flex flex-col min-h-full">
      <SiteHeader totalEditals={editals.length} lastSyncedAt={lastSyncedLabel} />

      <main className="flex-1">
        <PageIntro totalEditals={editals.length} />

        {/* Barra de busca */}
        <div className="mx-auto max-w-6xl px-6 pb-8">
          <SearchBar defaultValue={q} />
          {query && (
            <p className="mt-3 text-sm text-[var(--muted)]">
              {sorted.length === 0
                ? "Nenhum resultado para "
                : `${sorted.length} resultado${sorted.length !== 1 ? "s" : ""} para `}
              <span className="font-medium text-[var(--foreground)]">
                &ldquo;{q}&rdquo;
              </span>
            </p>
          )}
        </div>

        {/* Grid de cards */}
        <section className="mx-auto max-w-6xl px-6 pb-4">
          {editals.length === 0 ? (
            <EmptyState />
          ) : sorted.length === 0 ? (
            <NoResults query={q} />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {pageItems.map((edital) => (
                <EditalCard
                  key={edital.id}
                  edital={edital}
                  isNew={isNewEdital(edital.scrapedAt, edital.publishedAt)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Paginação */}
        {sorted.length > 0 && (
          <div className="mx-auto max-w-6xl px-6">
            <Pagination page={clampedPage} totalPages={totalPages} query={q} />
          </div>
        )}
      </main>

      <footer className="border-t border-[var(--border)]/70 bg-[var(--surface)]/40">
        <div className="mx-auto max-w-6xl px-6 py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-[var(--muted)]">
          <p>
            Apenas para acompanhamento; consulte o site oficial de cada
            processo.
          </p>
          <p className="font-mono">edital-tracker · v0.3</p>
        </div>
      </footer>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--border-strong)] bg-[var(--surface)]/60 px-6 py-16 text-center">
      <p className="text-[var(--foreground)] font-semibold text-lg">
        Nenhum edital no banco ainda.
      </p>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Rode{" "}
        <code className="font-mono bg-[var(--surface-muted)] px-1.5 py-0.5 rounded">
          python -m scraper
        </code>{" "}
        para popular o JSON com as últimas notícias.
      </p>
    </div>
  );
}

function NoResults({ query }: { query: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--border-strong)] bg-[var(--surface)]/60 px-6 py-16 text-center">
      <p className="text-[var(--foreground)] font-semibold text-lg">
        Nenhum edital encontrado para &ldquo;{query}&rdquo;.
      </p>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Tente outro termo — nome da instituição, especialidade ou ano.
      </p>
    </div>
  );
}
