/**
 * Tests for the Contrarian Analysis Strategy.
 */
import { describe, test, expect } from "./run.js";
import { analyzeContrarian } from "../strategies/contrarian.js";
import {
  makeMarket,
  makeHeavyFavorite,
  makeCoinFlip,
  makeClosingSoon,
  makeLongDated,
  makeRaceMarket,
  makeLowLiquidity,
  makeExtremeLongshot,
} from "./fixtures.js";

export function testContrarian() {
  describe("Contrarian: basic analysis", () => {
    test("returns correct strategy name", () => {
      const result = analyzeContrarian(makeMarket());
      expect(result.strategy).toBe("contrarian");
    });

    test("includes contrarian tag", () => {
      const result = analyzeContrarian(makeMarket());
      expect(result.tags).toContain("contrarian");
    });

    test("confidence is bounded", () => {
      const result = analyzeContrarian(makeMarket());
      expect(result.confidence).toBeGreaterThanOrEqual(5);
      expect(result.confidence).toBeLessThanOrEqual(85); // Contrarian caps at 85
    });
  });

  describe("Contrarian: crowd herding", () => {
    test("detects crowd herding on heavy favorites with low pool", () => {
      const result = analyzeContrarian(makeHeavyFavorite());
      expect(result.tags).toContain("crowd-herding");
      expect(result.signal).toBe("bearish"); // Against the crowd
    });
  });

  describe("Contrarian: extreme longshot", () => {
    test("analyzes extreme underdog", () => {
      const result = analyzeContrarian(makeExtremeLongshot());
      expect(result.reasoning.length).toBeGreaterThan(10);
    });
  });

  describe("Contrarian: coin flip with time pressure", () => {
    test("flags undecided late-stage markets", () => {
      const market = makeCoinFlip();
      market.closingTime = new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString();
      const result = analyzeContrarian(market);
      expect(result.tags).toContain("undecided-late");
    });
  });

  describe("Contrarian: pool asymmetry", () => {
    test("detects asymmetric payoff opportunity", () => {
      const market = makeMarket({
        pool: { total: 2.0, outcomes: [1.9, 0.1] },
        outcomes: [
          { index: 0, label: "Yes", probability: 0.95, pool: 1.9 },
          { index: 1, label: "No", probability: 0.05, pool: 0.1 },
        ],
      });
      const result = analyzeContrarian(market);
      expect(result.tags).toContain("asymmetric-payoff");
    });
  });

  describe("Contrarian: race market dark horse", () => {
    test("identifies dark horse in race market", () => {
      const market = makeRaceMarket();
      // Reduce pool to trigger dark-horse detection
      market.pool.total = 1.5;
      // Add a very low-probability outcome
      market.outcomes.push({
        index: 4,
        label: "Underdog Film",
        probability: 0.02,
        pool: 0.03,
      });
      const result = analyzeContrarian(market);
      expect(result.tags).toContain("dark-horse");
    });
  });

  describe("Contrarian: new market", () => {
    test("flags fresh low-liquidity markets", () => {
      const market = makeLowLiquidity();
      market.closingTime = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString();
      const result = analyzeContrarian(market);
      expect(result.tags).toContain("new-market");
      expect(result.confidence).toBeLessThanOrEqual(25);
    });
  });
}
