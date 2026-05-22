export type TimelineEntry = {
  label: string;
  date: string;
  isRange?: boolean;
};

export type Edital = {
  id: string;
  source: {
    name: string;
    shortName: string;
    accentColor: string;
  };
  originalTitle: string;
  rewrittenTitle: string;
  examYear: number;
  originalUrl: string;
  officialUrl?: string | null;
  /** ISO string gravado na primeira vez que o scraper viu este edital. Nunca atualizado. */
  scrapedAt?: string;
  publishedAt: string;
  updatedAt: string;
  timeline: TimelineEntry[];
  warningNote?: string | null;
};
