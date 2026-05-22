import type { TimelineEntry } from "@/types/edital";

const parseDmy = (value: string): Date | null => {
  const match = value.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (!match) return null;
  const [, dd, mm, yyyy] = match;
  return new Date(Number(yyyy), Number(mm) - 1, Number(dd));
};

const extractEffectiveDate = (entry: TimelineEntry): Date | null => {
  if (entry.isRange) {
    const tokens = entry.date.split(/\s+a\s+/);
    const start = tokens[0];
    const startMatch = start.match(/(\d{2})\/(\d{2})(?:\/(\d{4}))?/);
    if (!startMatch) return null;
    const [, dd, mm, yyyy] = startMatch;
    const yearFromEnd = entry.date.match(/\/(\d{4})\s*$/);
    const year = yyyy ?? yearFromEnd?.[1];
    if (!year) return null;
    return new Date(Number(year), Number(mm) - 1, Number(dd));
  }
  return parseDmy(entry.date);
};

export type NextMilestone = {
  entry: TimelineEntry;
  daysUntil: number;
};

export const findNextMilestone = (
  timeline: TimelineEntry[],
  today: Date = new Date(),
): NextMilestone | null => {
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  let best: NextMilestone | null = null;
  for (const entry of timeline) {
    const date = extractEffectiveDate(entry);
    if (!date) continue;
    if (date < todayStart) continue;
    const diff = Math.round((date.getTime() - todayStart.getTime()) / 86_400_000);
    if (!best || diff < best.daysUntil) {
      best = { entry, daysUntil: diff };
    }
  }
  return best;
};

/**
 * Retorna true se o edital foi visto pelo scraper há ≤ daysThreshold dias.
 * Usa scrapedAt como referência (quando disponível) ou cai para publishedAt.
 */
export const isNewEdital = (
  scrapedAt?: string | null,
  publishedAt?: string,
  daysThreshold = 2,
): boolean => {
  const ref = scrapedAt ?? publishedAt;
  if (!ref) return false;
  const diffDays = (Date.now() - new Date(ref).getTime()) / 86_400_000;
  return diffDays <= daysThreshold;
};

export const formatRelativeDays = (days: number): string => {
  if (days === 0) return "hoje";
  if (days === 1) return "amanhã";
  if (days < 30) return `em ${days} dias`;
  if (days < 60) return "em 1 mês";
  const months = Math.round(days / 30);
  if (months < 12) return `em ${months} meses`;
  return `em mais de 1 ano`;
};
