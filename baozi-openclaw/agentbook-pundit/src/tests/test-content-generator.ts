/**
 * Tests for the Content Generator.
 */
import { describe, test, expect } from "./run.js";
import {
  generateRoundup,
  generateOddsMovement,
  generateClosingSoon,
  generateDeepDive,
  generateContrarianTake,
  generateMarketComment,
  generateContent,
} from "../services/content-generator.js";
import { generateReport, analyzeMarketAll, getConsensus } from "../strategies/index.js";
import {
  makeMarket,
  makeHeavyFavorite,
  makeCoinFlip,
  makeClosingSoon,
  makeRaceMarket,
  makeExtremeLongshot,
  makeSportsMarket,
} from "./fixtures.js";

export function testContentGenerator() {
  const markets = [makeMarket(), makeHeavyFavorite(), makeCoinFlip(), makeSportsMarket()];
  const report = generateReport(markets);

  describe("Content: roundup", () => {
    test("generates non-empty roundup", () => {
      const content = generateRoundup(report);
      expect(content.length).toBeGreaterThan(50);
    });

    test("roundup stays under 2000 chars", () => {
      const content = generateRoundup(report);
      expect(content.length).toBeLessThanOrEqual(2000);
    });

    test("roundup contains market roundup header", () => {
      const content = generateRoundup(report);
      expect(content).toContain("Roundup");
    });
  });

  describe("Content: odds movement", () => {
    test("generates odds movement alert", () => {
      const content = generateOddsMovement(report.analyses);
      expect(content.length).toBeGreaterThan(20);
    });

    test("stays under 2000 chars", () => {
      const content = generateOddsMovement(report.analyses);
      expect(content.length).toBeLessThanOrEqual(2000);
    });
  });

  describe("Content: closing soon", () => {
    test("generates closing soon alert with closing markets", () => {
      const closingMarkets = [makeClosingSoon()];
      const content = generateClosingSoon(closingMarkets);
      expect(content).toContain("Closing Soon");
    });

    test("handles no closing markets", () => {
      const content = generateClosingSoon([]);
      expect(content).toContain("No markets closing");
    });
  });

  describe("Content: deep dive", () => {
    test("generates detailed analysis", () => {
      const content = generateDeepDive(report.analyses);
      expect(content).toContain("Deep Dive");
    });

    test("includes odds breakdown", () => {
      const content = generateDeepDive(report.analyses);
      expect(content).toContain("Odds breakdown");
    });

    test("stays under 2000 chars", () => {
      const content = generateDeepDive(report.analyses);
      expect(content.length).toBeLessThanOrEqual(2000);
    });
  });

  describe("Content: contrarian take", () => {
    test("generates contrarian content", () => {
      const analyses = report.analyses;
      const content = generateContrarianTake(analyses);
      expect(content.length).toBeGreaterThan(20);
    });

    test("stays under 2000 chars", () => {
      const content = generateContrarianTake(report.analyses);
      expect(content.length).toBeLessThanOrEqual(2000);
    });
  });

  describe("Content: market comment", () => {
    test("generates comment for analysis", () => {
      const analyses = analyzeMarketAll(makeMarket());
      const consensus = getConsensus(analyses)!;
      const comment = generateMarketComment(consensus);
      expect(comment.length).toBeGreaterThanOrEqual(10);
    });

    test("comment stays under 500 chars", () => {
      const analyses = analyzeMarketAll(makeMarket());
      const consensus = getConsensus(analyses)!;
      const comment = generateMarketComment(consensus);
      expect(comment.length).toBeLessThanOrEqual(500);
    });
  });

  describe("Content: generateContent factory", () => {
    test("generates roundup content", () => {
      const { content } = generateContent("roundup", report);
      expect(content.length).toBeGreaterThan(10);
    });

    test("generates deep-dive with market PDA", () => {
      const result = generateContent("deep-dive", report);
      expect(result.content.length).toBeGreaterThan(10);
    });
  });
}
