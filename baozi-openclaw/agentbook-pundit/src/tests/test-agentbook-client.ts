/**
 * Tests for the AgentBook Client (offline/unit tests).
 */
import { describe, test, expect } from "./run.js";
import { AgentBookClient } from "../services/agentbook-client.js";

export function testAgentBookClient() {
  const client = new AgentBookClient({
    walletAddress: "TestWallet123",
    dryRun: true,
  });

  describe("AgentBookClient: canPost", () => {
    test("allows posting when fresh", () => {
      const result = client.canPost();
      expect(result.allowed).toBeTruthy();
    });

    test("returns correct history initially", () => {
      const history = client.getHistory();
      expect(history.postsToday).toBe(0);
      expect(history.commentsToday).toBe(0);
    });
  });

  describe("AgentBookClient: canComment", () => {
    test("allows commenting when fresh", () => {
      const result = client.canComment();
      expect(result.allowed).toBeTruthy();
    });
  });

  describe("AgentBookClient: post validation", () => {
    test("rejects too-short posts", async () => {
      const result = await client.postTake("short");
      expect(result.success).toBeFalsy();
      expect(result.error).toContain("too short");
    });

    test("rejects too-long posts", async () => {
      const longContent = "x".repeat(2001);
      const result = await client.postTake(longContent);
      expect(result.success).toBeFalsy();
      expect(result.error).toContain("too long");
    });

    test("accepts valid-length posts in dry run", async () => {
      const result = await client.postTake("This is a valid post with enough characters for AgentBook.");
      expect(result.success).toBeTruthy();
    });
  });

  describe("AgentBookClient: comment validation", () => {
    test("rejects too-short comments", async () => {
      const result = await client.postComment("market-pda", "hi");
      expect(result.success).toBeFalsy();
      expect(result.error).toContain("too short");
    });

    test("rejects too-long comments", async () => {
      const longComment = "x".repeat(501);
      const result = await client.postComment("market-pda", longComment);
      expect(result.success).toBeFalsy();
      expect(result.error).toContain("too long");
    });

    test("accepts valid-length comments in dry run", async () => {
      const result = await client.postComment("market-pda", "This is a valid market comment for testing purposes.");
      expect(result.success).toBeTruthy();
    });
  });

  describe("AgentBookClient: daily counters", () => {
    test("resetDailyCounters clears state", () => {
      client.resetDailyCounters();
      const history = client.getHistory();
      expect(history.postsToday).toBe(0);
      expect(history.commentsToday).toBe(0);
      expect(history.postedMarketPdas.length).toBe(0);
    });
  });
}
