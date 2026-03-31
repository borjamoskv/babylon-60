/**
 * Tests for the Fundamental Analysis Strategy.
 */
import { describe, test, expect } from "./run.js";
import { analyzeFundamental } from "../strategies/fundamental.js";
import {
  makeMarket,
  makeHeavyFavorite,
  makeCoinFlip,
  makeClosingSoon,
  makeLongDated,
  makeRaceMarket,
  makeLowLiquidity,
  makeHighLiquidity,
  makeExpired,
  makeSportsMarket,
} from "./fixtures.js";

export function testFundamental() {
  describe("Fundamental: basic analysis", () => {
    test("returns correct strategy name", () => {
      const result = analyzeFundamental(makeMarket());
      expect(result.strategy).toBe("fundamental");
    });

    test("includes fundamental tag", () => {
      const result = analyzeFundamental(makeMarket());
      expect(result.tags).toContain("fundamental");
    });

    test("confidence is between 5 and 95", () => {
      const result = analyzeFundamental(makeMarket());
      expect(result.confidence).toBeGreaterThanOrEqual(5);
      expect(result.confidence).toBeLessThanOrEqual(95);
    });

    test("has non-empty reasoning", () => {
      const result = analyzeFundamental(makeMarket());
      expect(result.reasoning.length).toBeGreaterThan(10);
    });
  });

  describe("Fundamental: heavy favorite", () => {
    test("detects extreme odds", () => {
      const result = analyzeFundamental(makeHeavyFavorite());
      expect(result.signal).toBe("bullish");
      expect(result.reasoning).toContain("favorite");
    });

    test("flags low pool on heavy favorite", () => {
      const result = analyzeFundamental(makeHeavyFavorite());
      expect(result.tags).toContain("low-liquidity");
    });
  });

  describe("Fundamental: coin flip", () => {
    test("detects near 50/50 market", () => {
      const result = analyzeFundamental(makeCoinFlip());
      expect(result.signal).toBe("neutral");
      expect(result.tags).toContain("coin-flip");
    });
  });

  describe("Fundamental: closing soon", () => {
    test("detects closing-soon market", () => {
      const result = analyzeFundamental(makeClosingSoon());
      expect(result.tags).toContain("closing-soon");
    });
  });

  describe("Fundamental: long dated", () => {
    test("detects long-dated market", () => {
      const result = analyzeFundamental(makeLongDated());
      expect(result.tags).toContain("long-dated");
    });
  });

  describe("Fundamental: race market", () => {
    test("detects race market with multiple outcomes", () => {
      const result = analyzeFundamental(makeRaceMarket());
      expect(result.tags).toContain("race-market");
    });

    test("identifies tight race in race market", () => {
      const result = analyzeFundamental(makeRaceMarket());
      expect(result.reasoning).toContain("race");
    });
  });

  describe("Fundamental: liquidity", () => {
    test("flags low liquidity", () => {
      const result = analyzeFundamental(makeLowLiquidity());
      expect(result.tags).toContain("low-liquidity");
    });

    test("recognizes high liquidity", () => {
      const result = analyzeFundamental(makeHighLiquidity());
      expect(result.tags).toContain("high-liquidity");
    });
  });

  describe("Fundamental: expired", () => {
    test("gives zero confidence for expired market", () => {
      const result = analyzeFundamental(makeExpired());
      expect(result.confidence).toBe(5); // Clamped to minimum
    });
  });

  describe("Fundamental: sports", () => {
    test("boosts confidence for sports market", () => {
      const sports = analyzeFundamental(makeSportsMarket());
      const general = analyzeFundamental(makeMarket({ category: "general" }));
      // Sports gets a +5 boost
      expect(sports.reasoning).toContain("Sports");
    });
  });
}
