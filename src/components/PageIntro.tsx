type Props = {
  totalEditals: number;
};

export function PageIntro({ totalEditals }: Props) {
  return (
    <section className="mx-auto max-w-6xl px-6 pt-12 pb-8">
      <div className="flex flex-col gap-4 max-w-3xl">
        <span className="inline-flex items-center gap-2 self-start rounded-full border border-[var(--border)] bg-[var(--surface)]/70 px-3 py-1 text-xs font-medium text-[var(--muted)]">
          <span className="inline-flex size-1.5 rounded-full bg-emerald-500" />
          Fonte: Estratégia MED · atualizado continuamente
        </span>
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--foreground)]">
          Editais publicados em destaque
        </h2>
        <p className="text-[var(--muted)] text-base sm:text-lg leading-relaxed">
          {totalEditals} editais de residência médica e provas de título com
          cronograma consolidado, link para o site oficial e título reescrito
          de forma objetiva. Atualizações e processos sem edital publicado
          ficam de fora.
        </p>
      </div>
    </section>
  );
}
