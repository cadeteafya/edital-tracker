type Props = {
  totalEditals: number;
  lastSyncedAt: string;
};

export function SiteHeader({ totalEditals, lastSyncedAt }: Props) {
  return (
    <header className="border-b border-[var(--border)]/70 backdrop-blur-md bg-[color-mix(in_oklab,var(--background)_75%,transparent)] sticky top-0 z-20">
      <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-xl bg-gradient-to-br from-sky-500 to-teal-500 grid place-items-center text-white shadow-sm shadow-sky-500/20">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              className="size-5"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3v18M3 12h18" />
            </svg>
          </div>
          <div className="leading-tight">
            <h1 className="font-semibold text-[var(--foreground)] text-base">
              Edital Tracker
            </h1>
            <p className="text-xs text-[var(--muted)]">
              Residência médica & provas de título
            </p>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 text-xs text-[var(--muted)]">
          <span className="inline-flex size-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>
            {totalEditals} editais monitorados · sincronizado{" "}
            <time dateTime={lastSyncedAt}>{lastSyncedAt}</time>
          </span>
        </div>
      </div>
    </header>
  );
}
