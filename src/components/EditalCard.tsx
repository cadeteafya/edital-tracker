import type { Edital } from "@/types/edital";
import { findNextMilestone, formatRelativeDays } from "@/lib/dates";

type Props = {
  edital: Edital;
  isNew: boolean;
};

const formatPublishedAt = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

export function EditalCard({ edital, isNew }: Props) {
  const next = findNextMilestone(edital.timeline);

  return (
    <article
      className="group relative flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm overflow-hidden shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_18px_40px_-24px_rgba(2,6,23,0.25)] transition hover:border-[var(--border-strong)] hover:-translate-y-0.5 hover:shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_24px_50px_-20px_rgba(2,6,23,0.35)]"
      style={
        {
          "--card-accent": edital.source.accentColor,
        } as React.CSSProperties
      }
    >
      <div
        className="h-28 relative"
        style={{
          background: `linear-gradient(135deg, ${edital.source.accentColor} 0%, color-mix(in oklab, ${edital.source.accentColor} 55%, #0f172a) 100%)`,
        }}
      >
        <div className="absolute inset-0 opacity-30 mix-blend-overlay [background-image:radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.6),transparent_40%),radial-gradient(circle_at_80%_60%,rgba(255,255,255,0.4),transparent_45%)]" />
        <div className="relative h-full flex items-end justify-between px-5 pb-4">
          <div>
            {isNew && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/95 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-800">
                <span className="inline-flex size-1.5 rounded-full bg-emerald-500" />
                Saiu o edital
              </span>
            )}
            <p className="mt-2 text-white font-semibold text-lg leading-tight drop-shadow">
              {edital.source.shortName}
            </p>
          </div>
          <span className="rounded-md bg-black/30 px-2 py-1 text-[11px] font-mono text-white/90">
            {edital.examYear}
          </span>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-4 px-5 pt-5 pb-5">
        <header className="flex flex-col gap-2">
          <h3 className="text-[var(--foreground)] font-semibold text-base leading-snug">
            {edital.rewrittenTitle}
          </h3>
          <p className="text-xs text-[var(--muted)]">
            {edital.source.name} ·{" "}
            <span title={edital.originalTitle}>
              publicado em {formatPublishedAt(edital.publishedAt)}
            </span>
          </p>
        </header>

        {next && (
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-3.5 py-2.5 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-semibold">
                Próximo marco
              </p>
              <p className="text-sm font-medium text-[var(--foreground)] truncate">
                {next.entry.label}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-sm font-semibold text-[var(--foreground)] font-mono">
                {next.entry.date}
              </p>
              <p className="text-[11px] text-[var(--muted)]">
                {formatRelativeDays(next.daysUntil)}
              </p>
            </div>
          </div>
        )}

        {edital.timeline.length > 0 ? (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-[var(--muted)] font-semibold mb-2">
              Cronograma
            </p>
            <ol className="rounded-xl border border-[var(--border)] divide-y divide-[var(--border)] overflow-hidden">
              {edital.timeline.map((entry) => {
                const isNext = next?.entry.label === entry.label;
                return (
                  <li
                    key={entry.label}
                    className={`flex items-center justify-between gap-3 px-3.5 py-2 text-xs ${
                      isNext
                        ? "bg-[color-mix(in_oklab,var(--card-accent)_10%,transparent)]"
                        : ""
                    }`}
                  >
                    <span
                      className={`text-[var(--foreground)]/85 ${
                        isNext ? "font-medium" : ""
                      }`}
                    >
                      {entry.label}
                    </span>
                    <span className="font-mono text-[var(--muted)] tabular-nums">
                      {entry.date}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-[var(--muted)]">
            <svg
              viewBox="0 0 24 24"
              className="size-4 shrink-0 mt-0.5 opacity-50"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4m0 4h.01" />
            </svg>
            <span>
              Sem maiores informações sobre o processo — consulte a fonte
              oficial.
            </span>
          </div>
        )}

        <div className="mt-auto pt-1">
          {edital.officialUrl ? (
            <a
              href={edital.officialUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-[var(--foreground)] text-[var(--background)] px-3 py-2 text-xs font-semibold transition hover:opacity-90"
            >
              Site oficial
              <svg
                viewBox="0 0 24 24"
                className="size-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M7 17 17 7M9 7h8v8" />
              </svg>
            </a>
          ) : (
            <span className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-[var(--border-strong)] px-3 py-2 text-xs text-[var(--muted)] cursor-default select-none">
              Link oficial não encontrado
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
