import fs from "node:fs/promises";
import path from "node:path";

import type { Edital } from "@/types/edital";

type RawTimelineEntry = {
  label: string;
  date: string;
  isRange?: boolean;
};

type RawEdital = Omit<Edital, "timeline"> & {
  timeline: RawTimelineEntry[];
  revisions?: unknown[];
};

type Snapshot = {
  lastSyncedAt: string;
  editals: RawEdital[];
};

const DATA_PATH = path.join(process.cwd(), "data", "editals.json");

const EMPTY: Snapshot = { lastSyncedAt: new Date().toISOString(), editals: [] };

export async function loadEditalsSnapshot(): Promise<{
  lastSyncedAt: string;
  editals: Edital[];
}> {
  let raw: Snapshot;
  try {
    const file = await fs.readFile(DATA_PATH, "utf-8");
    raw = JSON.parse(file) as Snapshot;
  } catch {
    raw = EMPTY;
  }

  const editals: Edital[] = raw.editals.map((e) => ({
    id: e.id,
    source: e.source,
    originalTitle: e.originalTitle,
    rewrittenTitle: e.rewrittenTitle,
    examYear: e.examYear,
    originalUrl: e.originalUrl,
    officialUrl: e.officialUrl,
    scrapedAt: e.scrapedAt,
    publishedAt: e.publishedAt,
    updatedAt: e.updatedAt,
    timeline: e.timeline.map((t) => ({
      label: t.label,
      date: t.date,
      isRange: t.isRange,
    })),
    warningNote: e.warningNote,
  }));

  return { lastSyncedAt: raw.lastSyncedAt, editals };
}
