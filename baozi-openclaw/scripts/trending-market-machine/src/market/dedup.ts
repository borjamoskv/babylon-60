// Deduplication and state management for the Trending Market Machine
import { type TrendingTopic, type CreatedMarket } from "../config.ts";

// In-memory state (persisted to disk between runs)
interface MachineState {
  seenTopics: Record<string, number>; // topic ID -> timestamp
  createdMarkets: CreatedMarket[];
  lastRun: string;
}

const STATE_FILE = "trending-machine-state.json";

let state: MachineState = {
  seenTopics: {},
  createdMarkets: [],
  lastRun: new Date().toISOString(),
};

export async function loadState(): Promise<void> {
  try {
    const file = Bun.file(STATE_FILE);
    if (await file.exists()) {
      state = await file.json();
    }
  } catch {
    // Fresh state
  }
}

export async function saveState(): Promise<void> {
  state.lastRun = new Date().toISOString();
  await Bun.write(STATE_FILE, JSON.stringify(state, null, 2));
}

export function isTopicSeen(topic: TrendingTopic): boolean {
  return topic.id in state.seenTopics;
}

export function markTopicSeen(topic: TrendingTopic): void {
  state.seenTopics[topic.id] = Date.now();
}

export function recordCreatedMarket(market: CreatedMarket): void {
  state.createdMarkets.push(market);
}

export function getCreatedMarketsFromState(): CreatedMarket[] {
  return state.createdMarkets;
}

// Clean up old entries (>7 days)
export function pruneState(): void {
  const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
  for (const [id, ts] of Object.entries(state.seenTopics)) {
    if (ts < cutoff) delete state.seenTopics[id];
  }
  state.createdMarkets = state.createdMarkets.filter(
    (m) => new Date(m.createdAt).getTime() > cutoff
  );
}

// Cross-source topic merging: boost score if same topic appears in multiple sources
export function mergeTopics(topics: TrendingTopic[]): TrendingTopic[] {
  const merged = new Map<string, TrendingTopic>();

  for (const topic of topics) {
    // Generate a fuzzy key from the title
    const key = topic.title
      .toLowerCase()
      .replace(/[^a-z0-9 ]/g, "")
      .split(" ")
      .filter((w) => w.length > 3)
      .sort()
      .join("-");

    const existing = merged.get(key);
    if (existing) {
      // Boost score for cross-source confirmation
      existing.score = Math.min(100, existing.score + 20);
      existing.metadata.crossSourceConfirmed = true;
      existing.metadata.sources = [
        ...(existing.metadata.sources as string[] || [existing.source]),
        topic.source,
      ];
    } else {
      merged.set(key, { ...topic, metadata: { ...topic.metadata, sources: [topic.source] } });
    }
  }

  return [...merged.values()];
}
