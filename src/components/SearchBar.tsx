"use client";

import { useRouter, usePathname } from "next/navigation";
import { useRef, useTransition } from "react";

type Props = {
  defaultValue?: string;
};

export function SearchBar({ defaultValue = "" }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const timer = useRef<ReturnType<typeof setTimeout>>(null);

  const navigate = (value: string) => {
    startTransition(() => {
      const params = new URLSearchParams();
      if (value.trim()) params.set("q", value.trim());
      // sempre volta para a página 1 numa nova busca
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname);
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (timer.current) clearTimeout(timer.current);
    const value = e.target.value;
    timer.current = setTimeout(() => navigate(value), 350);
  };

  const handleClear = () => {
    if (timer.current) clearTimeout(timer.current);
    navigate("");
  };

  return (
    <div className="relative w-full max-w-md">
      {/* ícone lupa */}
      <svg
        viewBox="0 0 24 24"
        className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-[var(--muted)]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>

      <input
        key={defaultValue}          /* força re-mount ao navegar de volta */
        type="search"
        defaultValue={defaultValue}
        onChange={handleChange}
        placeholder="Buscar por instituição ou especialidade…"
        className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)]/80 py-2.5 pl-10 pr-10 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] outline-none ring-0 transition focus:border-[var(--border-strong)] focus:ring-2 focus:ring-[var(--accent)]/20 backdrop-blur-sm"
      />

      {/* spinner ou botão de limpar */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 size-4">
        {isPending ? (
          <svg
            className="animate-spin text-[var(--muted)]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden
          >
            <path
              strokeLinecap="round"
              d="M12 3a9 9 0 1 0 9 9"
            />
          </svg>
        ) : defaultValue ? (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Limpar busca"
            className="flex items-center justify-center size-4 rounded-full text-[var(--muted)] hover:text-[var(--foreground)] transition"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        ) : null}
      </div>
    </div>
  );
}
