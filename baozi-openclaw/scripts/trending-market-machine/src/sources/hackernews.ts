// HackerNews trending stories source
import { CONFIG, type TrendingTopic, type Category } from "../config.ts";

interface HNStory {
  id: number;
  title: string;
  url?: string;
  score: number;
  by: string;
  time: number;
  descendants: number;
}

function classifyStory(title: string): Category {
  const lower = title.toLowerCase();
  if (lower.match(/\b(crypto|bitcoin|btc|ethereum|eth|solana|sol|defi|nft|token|blockchain|web3)\b/)) return "crypto";
  if (lower.match(/\b(ai|llm|gpt|claude|openai|anthropic|model|neural|machine learning|ml)\b/)) return "technology";
  if (lower.match(/\b(apple|google|meta|microsoft|amazon|tesla|nvidia|startup|launch|funding)\b/)) return "technology";
  if (lower.match(/\b(election|vote|congress|president|senate|bill|regulation|policy)\b/)) return "politics";
  if (lower.match(/\b(study|research|paper|discovery|genome|physics|space|nasa)\b/)) return "science";
  return "technology";
}

// Filter stories that could become good prediction markets
function isMarketable(story: HNStory): boolean {
  const title = story.title.toLowerCase();
  // Look for forward-looking topics (launches, announcements, events)
  const forwardLooking = title.match(/\b(will|launch|announce|release|plan|expect|upcoming|new|introduce|reveal)\b/);
  // Look for measurable events
  const measurable = title.match(/\b(reach|hit|pass|surpass|exceed|break|cross|milestone|record)\b/);
  // Look for competition/comparison
  const competitive = title.match(/\b(vs|versus|compete|challenge|beat|overtake|race)\b/);
  // High engagement = high interest
  const highEngagement = story.score > 200 || story.descendants > 100;

  return !!(forwardLooking || measurable || competitive || highEngagement);
}

export async function fetchHackerNewsTrends(): Promise<TrendingTopic[]> {
  // Get top stories
  const topResp = await fetch(`${CONFIG.HN_API}/topstories.json`);
  if (!topResp.ok) return [];
  const topIds: number[] = await topResp.json();

  // Fetch top 30 stories
  const stories = await Promise.all(
    topIds.slice(0, 30).map(async (id) => {
      const resp = await fetch(`${CONFIG.HN_API}/item/${id}.json`);
      return resp.ok ? (await resp.json()) as HNStory : null;
    })
  );

  return stories
    .filter((s): s is HNStory => s !== null && isMarketable(s))
    .slice(0, 5)
    .map((story) => ({
      id: `hn-${story.id}`,
      title: story.title,
      source: "hackernews",
      category: classifyStory(story.title),
      url: story.url || `https://news.ycombinator.com/item?id=${story.id}`,
      score: Math.min(100, Math.floor(story.score / 5) + (story.descendants / 2)),
      detectedAt: new Date(),
      metadata: {
        hnId: story.id,
        points: story.score,
        comments: story.descendants,
        by: story.by,
        time: story.time,
      },
    }));
}
