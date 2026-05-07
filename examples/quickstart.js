/**
 * CORTEX Quickstart — JavaScript/TypeScript
 *
 * Usage:
 *   node quickstart.js
 *
 * No dependencies required — uses native fetch (Node 18+).
 */

const BASE_URL = "http://localhost:8484";
const API_KEY = "<YOUR_API_KEY>";

const headers = {
  "Content-Type": "application/json",
  "Authorization": `Bearer ${API_KEY}`,
};

async function main() {
  // 1. Store a fact
  console.log("Storing fact...");
  const storeResp = await fetch(`${BASE_URL}/v1/facts`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      content:
        "CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.",
      fact_type: "knowledge",
      project: "demo",
    }),
  });
  const stored = await storeResp.json();
  console.log(`  Stored fact #${stored.fact_id}`);

  // 2. Search
  console.log("\nSearching...");
  const searchResp = await fetch(`${BASE_URL}/v1/facts/search`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query: "sovereign memory", k: 3 }),
  });
  const results = await searchResp.json();
  for (const r of results.results || results) {
    console.log(`  [#${r.fact_id}] (score: ${r.score?.toFixed(3)}) ${r.content?.slice(0, 80)}`);
  }

  // 3. Ask (RAG)
  console.log("\nAsking...");
  try {
    const askResp = await fetch(`${BASE_URL}/v1/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query: "What is CORTEX?", k: 5 }),
    });
    const answer = await askResp.json();
    console.log(`  Answer: ${answer.answer}`);
  } catch (e) {
    console.log(`  RAG requires CORTEX_ENABLE_EXPERIMENTAL_API=1 and an LLM provider: ${e.message}`);
  }

  console.log("\nCORTEX is operational!");
}

main().catch(console.error);
