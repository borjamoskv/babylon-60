/**
 * Tests for the Statistical Analysis Strategy.
 */
import { describe, test, expect } from "./run.js";
import { analyzeStatistical } from "../strategies/statistical.js";
import {
  makeMarket,
  makeHeavyFavorite,
  makeCoinFlip,
  makeLowLiquidity,
  makeHighLiquidity,
  makeRaceMarket,
  makeExtremeLongshot,
} from "./fixtures.js";

export function testStatistical() {
  describe("Statistical: basic analysis", () => {
    test("returns correct strategy name", () => {
      const result = analyzeStatistical(makeMarket());
      expect(result.strategy).toBe("statistical");
    });

    test("includes statistical tag", () => {
      const result = analyzeStatistical(makeMarket());
      expect(result.tags).toContain("statistical");
    });

    test("confidence is bounded", () => {
      const result = analyzeStatistical(makeMarket());
      expect(result.confidence).toBeGreaterThanOrEqual(5);
      expect(result.confidence).toBeLessThanOrEqual(95);
    });
  });

  describe("Statistical: pool concentration", () => {
    test("detects concentrated pool", () => {
      const market = makeHeavyFavorite();
      const result = analyzeStatistical(market);
      expect(result.tags).toContain("concentrated");
    });

    test("detects balanced pool", () => {
      const result = analyzeStatistical(makeCoinFlip());
      expect(result.tags).toContain("balanced");
    });
  });

  describe("Statistical: implied returns", () => {
    test("identifies longshot returns", () => {
      const result = analyzeStatistical(makeExtremeLongshot());
      expect(result.tags).toContain("longshot");
    });
  });

  describe("Statistical: volume weighting", () => {
    test("increases confidence for high-pool markets", () => {
      const highLiq = analyzeStatistical(makeHighLiquidity());
      const lowLiq = analyzeStatistical(makeLowLiquidity());
      expect(highLiq.confidence).toBeGreaterThan(lowLiq.confidence);
    });
  });

  describe("Statistical: race market", () => {
    test("analyzes multi-outcome markets", () => {
      const result = analyzeStatistical(makeRaceMarket());
      expect(result.reasoning.length).toBeGreaterThan(10);
    });
  });

  describe("Statistical: Kelly criterion", () => {
    test("provides Kelly analysis for binary markets", () => {
      const result = analyzeStatistical(makeMarket());
      expect(result.reasoning).toContain("Kelly");
    });
  });
}
