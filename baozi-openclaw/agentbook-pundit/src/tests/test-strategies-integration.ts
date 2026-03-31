/**
 * Integration tests across multiple strategies.
 */
import { describe, test, expect } from "./run.js";
import {
  analyzeMarket,
  analyzeMarketAll,
  getConsensus,
  generateReport,
} from "../strategies/index.js";
import {
  makeMarket,
  makeHeavyFavorite,
  makeCoinFlip,
  makeRaceMarket,
  makeClosingSoon,
  makeHighLiquidity,
  makeLowLiquidity,
  makeExtremeLongshot,
  makeSportsMarket,
} from "./fixtures.js";

export function testStrategiesIntegration() {
  describe("Integration: analyzeMarket", () => {
    test("dispatches to fundamental strategy", () => {
      const result = analyzeMarket(makeMarket(), "fundamental");
      expect(result.strategy).toBe("fundamental");
    });

    test("dispatches to statistical strategy", () => {
      const result = analyzeMarket(makeMarket(), "statistical");
      expect(result.strategy).toBe("statistical");
    });

    test("dispatches to contrarian strategy", () => {
      const result = analyzeMarket(makeMarket(), "contrarian");
      expect(result.strategy).toBe("contrarian");
    });
  });

  describe("Integration: analyzeMarketAll", () => {
    test("returns 3 analyses", () => {
      const results = analyzeMarketAll(makeMarket());
      expect(results.length).toBe(3);
    });

    test("covers all strategies", () => {
      const results = analyzeMarketAll(makeMarket());
      const strategies = results.map((r) => r.strategy);
      expect(strategies).toContain("fundamental");
      expect(strategies).toContain("statistical");
      expect(strategies).toContain("contrarian");
    });
  });

  describe("Integration: getConsensus", () => {
    test("returns consensus from multiple analyses", () => {
      const analyses = analyzeMarketAll(makeMarket());
      const consensus = getConsensus(analyses);
      expect(consensus).toBeTruthy();
      expect(consensus!.confidence).toBeGreaterThan(0);
    });

    test("handles empty analyses", () => {
      const consensus = getConsensus([]);
      expect(consensus).toBe(null);
    });

    test("consensus confidence is bounded", () => {
      const analyses = analyzeMarketAll(makeHighLiquidity());
      const consensus = getConsensus(analyses);
      expect(consensus!.confidence).toBeGreaterThanOrEqual(5);
      expect(consensus!.confidence).toBeLessThanOrEqual(95);
    });
  });

  describe("Integration: generateReport", () => {
    test("generates report for multiple markets", () => {
      const markets = [makeMarket(), makeCoinFlip(), makeRaceMarket()];
      const report = generateReport(markets);
      expect(report.analyses.length).toBe(3);
    });

    test("report has summary", () => {
      const markets = [makeMarket()];
      const report = generateReport(markets);
      expect(report.summary.length).toBeGreaterThan(0);
    });

    test("report has top pick", () => {
      const markets = [makeMarket(), makeHeavyFavorite(), makeSportsMarket()];
      const report = generateReport(markets);
      expect(report.topPick).toBeTruthy();
    });

    test("report is sorted by confidence", () => {
      const markets = [makeMarket(), makeCoinFlip(), makeHighLiquidity(), makeLowLiquidity()];
      const report = generateReport(markets);
      for (let i = 1; i < report.analyses.length; i++) {
        expect(report.analyses[i - 1].confidence).toBeGreaterThanOrEqual(
          report.analyses[i].confidence
        );
      }
    });

    test("handles empty market list", () => {
      const report = generateReport([]);
      expect(report.analyses.length).toBe(0);
      expect(report.topPick).toBe(undefined);
    });
  });

  describe("Integration: edge cases", () => {
    test("extreme longshot gets analyzed by all strategies", () => {
      const results = analyzeMarketAll(makeExtremeLongshot());
      expect(results.length).toBe(3);
      for (const r of results) {
        expect(r.confidence).toBeGreaterThanOrEqual(5);
      }
    });

    test("closing-soon market flagged consistently", () => {
      const results = analyzeMarketAll(makeClosingSoon());
      const fundamental = results.find((r) => r.strategy === "fundamental")!;
      expect(fundamental.tags).toContain("closing-soon");
    });
  });
}
