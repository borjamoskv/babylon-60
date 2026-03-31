/**
 * Tests for utility helpers.
 */
import { describe, test, expect } from "./run.js";
import {
  hoursUntil,
  formatSol,
  formatPercent,
  categorizeQuestion,
  truncate,
  marketUrl,
  formatDate,
} from "../utils/helpers.js";

export function testHelpers() {
  describe("Utils: hoursUntil", () => {
    test("returns positive hours for future date", () => {
      const future = new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString();
      const hours = hoursUntil(future);
      expect(Math.round(hours)).toBe(3);
    });

    test("returns negative hours for past date", () => {
      const past = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      const hours = hoursUntil(past);
      expect(hours).toBeLessThan(0);
    });
  });

  describe("Utils: formatSol", () => {
    test("formats large amounts with K suffix", () => {
      expect(formatSol(1500)).toBe("1.5K SOL");
    });

    test("formats normal amounts with 2 decimals", () => {
      expect(formatSol(5.123)).toBe("5.12 SOL");
    });

    test("formats small amounts with 3 decimals", () => {
      expect(formatSol(0.05)).toBe("0.050 SOL");
    });

    test("formats tiny amounts with 4 decimals", () => {
      expect(formatSol(0.005)).toBe("0.0050 SOL");
    });
  });

  describe("Utils: formatPercent", () => {
    test("formats decimal as percentage", () => {
      expect(formatPercent(0.6)).toBe("60.0%");
    });

    test("formats 1.0 as 100%", () => {
      expect(formatPercent(1.0)).toBe("100.0%");
    });

    test("formats 0 as 0%", () => {
      expect(formatPercent(0)).toBe("0.0%");
    });
  });

  describe("Utils: categorizeQuestion", () => {
    test("categorizes crypto questions", () => {
      expect(categorizeQuestion("Will BTC hit $100k?")).toBe("crypto");
    });

    test("categorizes sports questions", () => {
      expect(categorizeQuestion("Will the Lakers win the NBA Championship?")).toBe("sports");
    });

    test("categorizes politics questions", () => {
      expect(categorizeQuestion("Will Trump win the election?")).toBe("politics");
    });

    test("categorizes entertainment questions", () => {
      expect(categorizeQuestion("Will the movie win a BAFTA?")).toBe("entertainment");
    });

    test("categorizes tech questions", () => {
      expect(categorizeQuestion("Will OpenAI release GPT-5?")).toBe("tech");
    });

    test("defaults to general", () => {
      expect(categorizeQuestion("Will something happen?")).toBe("general");
    });
  });

  describe("Utils: truncate", () => {
    test("returns short text unchanged", () => {
      expect(truncate("hello", 10)).toBe("hello");
    });

    test("truncates long text with ellipsis", () => {
      const result = truncate("this is a very long text", 15);
      expect(result.length).toBeLessThanOrEqual(15);
      expect(result).toContain("...");
    });
  });

  describe("Utils: marketUrl", () => {
    test("generates correct market URL", () => {
      expect(marketUrl("abc123")).toBe("baozi.bet/market/abc123");
    });
  });
}
