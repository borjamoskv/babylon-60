// RSS feed trending source — tech, crypto, sports news
import { type TrendingTopic, type Category } from "../config.ts";

interface RSSFeed {
  name: string;
  url: string;
  category: Category;
}

const FEEDS: RSSFeed[] = [
  { name: "CoinDesk", url: "https://www.coindesk.com/arc/outboundfeeds/rss/", category: "crypto" },
  { name: "The Block", url: "https://www.theblock.co/rss.xml", category: "crypto" },
  { name: "TechCrunch", url: "https://techcrunch.com/feed/", category: "technology" },
  { name: "Ars Technica", url: "https://feeds.arstechnica.com/arstechnica/index", category: "technology" },
  { name: "ESPN Top", url: "https://www.espn.com/espn/rss/news", category: "sports" },
];

interface RSSItem {
  title: string;
  link: string;
  pubDate?: string;
  description?: string;
}

// Minimal RSS/Atom parser (no dependencies)
function parseRSS(xml: string): RSSItem[] {
  const items: RSSItem[] = [];
  // Match <item> or <entry> blocks
  const itemRegex = /<(?:item|entry)[\s>]([\s\S]*?)<\/(?:item|entry)>/gi;
  let match;
  while ((match = itemRegex.exec(xml)) !== null) {
    const block = match[1];
    const title = block.match(/<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/title>/s)?.[1]?.trim();
    const link = block.match(/<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/link>/s)?.[1]?.trim()
      || block.match(/<link[^>]*href="([^"]*)"[^>]*\/>/)?.[1]?.trim();
    const pubDate = block.match(/<(?:pubDate|published|updated)[^>]*>(.*?)<\/(?:pubDate|published|updated)>/s)?.[1]?.trim();
    const description = block.match(/<description[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/description>/s)?.[1]?.trim();

    if (title) {
      items.push({ title, link: link || "", pubDate, description: description?.slice(0, 200) });
    }
  }
  return items;
}

function isForwardLooking(title: string): boolean {
  const lower = title.toLowerCase();
  return !!lower.match(/\b(will|launch|announce|release|plan|upcoming|set to|expected|reveal|unveil|debut|introduce|partnership|acquire|merge|ipo|listing)\b/);
}

export async function fetchRSSFeeds(): Promise<TrendingTopic[]> {
  const topics: TrendingTopic[] = [];
  const now = Date.now();

  for (const feed of FEEDS) {
    try {
      const resp = await fetch(feed.url, {
        headers: { "User-Agent": "TrendingMarketMachine/1.0" },
        signal: AbortSignal.timeout(10000),
      });
      if (!resp.ok) continue;

      const xml = await resp.text();
      const items = parseRSS(xml);

      for (const item of items.slice(0, 10)) {
        // Only include recent items (< 24h)
        if (item.pubDate) {
          const pubTime = new Date(item.pubDate).getTime();
          if (now - pubTime > 24 * 60 * 60 * 1000) continue;
        }

        if (!isForwardLooking(item.title)) continue;

        topics.push({
          id: `rss-${feed.name.toLowerCase()}-${Buffer.from(item.title).toString("base64").slice(0, 16)}`,
          title: item.title,
          source: `rss:${feed.name}`,
          category: feed.category,
          url: item.link,
          score: 50, // Base score for RSS items; can be boosted by cross-source confirmation
          detectedAt: new Date(),
          metadata: {
            feedName: feed.name,
            description: item.description,
            pubDate: item.pubDate,
          },
        });
      }
    } catch (err) {
      console.error(`RSS fetch failed for ${feed.name}:`, (err as Error).message);
    }
  }

  return topics;
}
