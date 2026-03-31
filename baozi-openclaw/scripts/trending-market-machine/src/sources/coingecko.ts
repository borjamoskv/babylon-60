// CoinGecko trending coins source
import { CONFIG, type TrendingTopic } from "../config.ts";

interface CoinGeckoTrending {
  coins: Array<{
    item: {
      id: string;
      coin_id: number;
      name: string;
      symbol: string;
      market_cap_rank: number;
      thumb: string;
      score: number;
      data?: {
        price: number;
        price_change_percentage_24h?: Record<string, number>;
        market_cap?: string;
        total_volume?: string;
      };
    };
  }>;
}

export async function fetchCoinGeckoTrends(): Promise<TrendingTopic[]> {
  const resp = await fetch(`${CONFIG.COINGECKO_API}/search/trending`);
  if (!resp.ok) {
    console.error(`CoinGecko API error: ${resp.status}`);
    return [];
  }

  const data: CoinGeckoTrending = await resp.json();
  const topics: TrendingTopic[] = [];

  for (const { item: coin } of data.coins.slice(0, 7)) {
    const priceChange = coin.data?.price_change_percentage_24h?.usd ?? 0;

    // Only create markets for coins with significant price movement or high rank
    if (Math.abs(priceChange) < 10 && (coin.market_cap_rank ?? 999) > 100) continue;

    topics.push({
      id: `coingecko-${coin.id}`,
      title: `${coin.name} (${coin.symbol.toUpperCase()}) trending on CoinGecko`,
      source: "coingecko",
      category: "crypto",
      url: `https://www.coingecko.com/en/coins/${coin.id}`,
      score: Math.min(100, (100 - (coin.score ?? 50)) + Math.abs(priceChange)),
      detectedAt: new Date(),
      metadata: {
        coinId: coin.id,
        name: coin.name,
        symbol: coin.symbol,
        marketCapRank: coin.market_cap_rank,
        priceChangePercent24h: priceChange,
        price: coin.data?.price,
      },
    });
  }

  return topics;
}
