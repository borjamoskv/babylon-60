import crypto from "node:crypto";

const DEFAULT_PUBLIC_ORIGIN = "https://cortexpersist.com";
const DEFAULT_ALLOWED_ORIGINS = [
  "https://cortexpersist.com",
  "https://www.cortexpersist.com",
  "https://cortexpersist.dev",
  "https://cortexpersist.org",
];
const PROOF_MARK_KEY = "cortex:proof-marks:v1";
const PROOF_MARK_SEQUENCE_KEY = "cortex:proof-marks:sequence:v1";
const PROOF_MARK_RATE_PREFIX = "cortex:proof-marks:rate:v1";
const PROOF_MARK_LIMIT = 192;
const PROOF_MARK_RATE_LIMIT = 120;
const PROOF_MARK_HUES = ["#d7ff5f", "#6ba6ff", "#38d39f", "#ffb45c"];
const MEDIA_MARK_KEY = "media:curation:marks:v1";
const MEDIA_MARK_SEQUENCE_KEY = "media:curation:marks:sequence:v1";
const MEDIA_MARK_RATE_PREFIX = "media:curation:marks:rate:v1";
const MEDIA_MARK_LIMIT = 260;
const MEDIA_MARK_RATE_LIMIT = 180;
const MEDIA_MARK_HUES = ["#d6b25e", "#1db954", "#ff3b30", "#88d9ff", "#f2efe9"];

const ALLOWED_PROOF_MARK_SECTIONS = new Set([
  "hero",
  "compliance",
  "workflow",
  "evidence",
  "crypto-nft-evidence",
  "use-cases",
  "features",
  "api-surface",
  "agent-control",
  "research",
  "crypto-tax",
  "fiscal-checklist",
  "use-cases-live",
  "reference-agent",
  "compare",
  "faq",
  "deployment",
  "pricing",
  "start",
  "page",
]);
const ALLOWED_MEDIA_MARK_SECTIONS = new Set(["top", "playlist", "archivo", "criterio", "page"]);

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(payload));
}

function setCors(req, res) {
  const origin = req.headers.origin;
  if (origin && allowedOrigins().includes(origin.replace(/\/$/, ""))) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function csvEnv(name) {
  return (process.env[name] || "")
    .split(",")
    .map((item) => item.trim().replace(/\/$/, ""))
    .filter(Boolean);
}

function allowedOrigins() {
  return csvEnv("CORTEX_CHECKOUT_ALLOWED_ORIGINS").length
    ? csvEnv("CORTEX_CHECKOUT_ALLOWED_ORIGINS")
    : csvEnv("CORTEX_ALLOWED_ORIGINS").length
      ? csvEnv("CORTEX_ALLOWED_ORIGINS")
      : DEFAULT_ALLOWED_ORIGINS;
}

function publicOrigin() {
  const raw = (process.env.CORTEX_PUBLIC_ORIGIN || DEFAULT_PUBLIC_ORIGIN).trim().replace(/\/$/, "");
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || !url.host) return DEFAULT_PUBLIC_ORIGIN;
    return url.origin;
  } catch {
    return DEFAULT_PUBLIC_ORIGIN;
  }
}

function originFor(candidate) {
  try {
    const url = new URL(candidate);
    if (url.protocol !== "https:" || !url.host) return null;
    return url.origin;
  } catch {
    return null;
  }
}

function safeReturnUrl(candidate, fallbackPath) {
  const fallback = publicOrigin() + fallbackPath;
  if (!candidate) return fallback;
  const origin = originFor(candidate);
  return origin && allowedOrigins().includes(origin) ? candidate : fallback;
}

function parsePriceTable() {
  if (!process.env.STRIPE_PRICE_TABLE) return {};
  try {
    const table = JSON.parse(process.env.STRIPE_PRICE_TABLE);
    if (!table || typeof table !== "object" || Array.isArray(table)) return null;
    return Object.fromEntries(Object.entries(table).filter(([, value]) => Boolean(value)));
  } catch {
    return null;
  }
}

function configuredBillingPlans() {
  const table = parsePriceTable();
  if (!table) return null;
  return Object.entries(table)
    .filter(([plan, priceId]) => ["pro", "team"].includes(plan) && Boolean(priceId))
    .map(([plan]) => plan);
}

function readinessPayload() {
  const storageConfigured = Boolean(redisConfig());
  const plans = configuredBillingPlans();
  const billingConfigured = Array.isArray(plans) && plans.length > 0 && Boolean((process.env.STRIPE_SECRET_KEY || "").trim());
  return {
    service: "cortex-saas-api",
    status: storageConfigured || billingConfigured ? "partial" : "needs_configuration",
    storage: {
      proofMarks: storageConfigured,
      mediaMarks: storageConfigured,
    },
    billing: {
      checkout: billingConfigured,
      plans: plans || [],
      priceTableValid: plans !== null,
    },
  };
}

async function readJsonBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") return JSON.parse(req.body || "{}");
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return raw ? JSON.parse(raw) : {};
}

function redisConfig() {
  const url = (process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL || "").trim().replace(/\/$/, "");
  const token = (process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN || "").trim();
  if (!url || !token) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !parsed.host) return null;
    return { url, token };
  } catch {
    return null;
  }
}

async function redisCommand(command) {
  const config = redisConfig();
  if (!config) {
    const error = new Error("Proof mark storage is not configured");
    error.statusCode = 503;
    throw error;
  }
  const response = await fetch(config.url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(command),
  });
  if (!response.ok) {
    const error = new Error("Proof mark storage is unavailable");
    error.statusCode = 503;
    throw error;
  }
  const payload = await response.json();
  if (payload && payload.error) {
    const error = new Error("Proof mark storage is unavailable");
    error.statusCode = 503;
    throw error;
  }
  return payload ? payload.result : null;
}

function coerceInt(value, fallback = 0) {
  const parsed = Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function boundedRateLimit(name, fallback, max) {
  const parsed = coerceInt(process.env[name], fallback);
  return Math.max(1, Math.min(parsed, max));
}

async function enforceRateLimit(prefix, limit, detail) {
  const minute = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
  const key = `${prefix}:${minute}`;
  const count = coerceInt(await redisCommand(["INCR", key]));
  if (count === 1) await redisCommand(["EXPIRE", key, 90]);
  if (count > limit) {
    const error = new Error(detail);
    error.statusCode = 429;
    throw error;
  }
}

function coarseRatio(value, steps) {
  return Math.round(value * steps) / steps;
}

function cleanSection(section, allowed) {
  const normalized = String(section || "page").trim().toLowerCase();
  return allowed.has(normalized) ? normalized : "page";
}

function currentHour() {
  const now = new Date();
  now.setUTCMinutes(0, 0, 0);
  return now.toISOString().replace(".000Z", "Z");
}

function markHash(namespace, sequence, section, x, y, timestamp) {
  return crypto
    .createHash("sha256")
    .update(`${namespace}|${sequence}|${section}|${x.toFixed(4)}|${y.toFixed(4)}|${timestamp}`)
    .digest("hex")
    .slice(0, 16);
}

function validateMarkBody(body) {
  const x = Number(body && body.x);
  const y = Number(body && body.y);
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1) {
    const error = new Error("Invalid proof mark payload");
    error.statusCode = 422;
    throw error;
  }
  return { x, y, section: String((body && body.section) || "page").slice(0, 64) };
}

function proofMarkFromBody(body, sequence) {
  const valid = validateMarkBody(body);
  const section = cleanSection(valid.section, ALLOWED_PROOF_MARK_SECTIONS);
  const x = coarseRatio(valid.x, 48);
  const y = coarseRatio(valid.y, 160);
  const timestamp = currentHour();
  return {
    x,
    y,
    section,
    t: timestamp,
    hue: PROOF_MARK_HUES[sequence % PROOF_MARK_HUES.length],
    hash: markHash("cortex", sequence, section, x, y, timestamp),
  };
}

function mediaMarkFromBody(body, sequence) {
  const valid = validateMarkBody(body);
  const section = cleanSection(valid.section, ALLOWED_MEDIA_MARK_SECTIONS);
  const x = coarseRatio(valid.x, 56);
  const y = coarseRatio(valid.y, 180);
  const timestamp = currentHour();
  return {
    x,
    y,
    section,
    t: timestamp,
    hue: MEDIA_MARK_HUES[sequence % MEDIA_MARK_HUES.length],
    hash: markHash("media-curation", sequence, section, x, y, timestamp),
  };
}

function decodeMark(value, defaultHue) {
  try {
    const parsed = JSON.parse(Buffer.isBuffer(value) ? value.toString("utf8") : String(value));
    if (!parsed || typeof parsed !== "object") return null;
    if (!["x", "y", "section", "t", "hash"].every((key) => key in parsed)) return null;
    return {
      x: parsed.x,
      y: parsed.y,
      section: parsed.section,
      t: parsed.t,
      hue: parsed.hue || defaultHue,
      hash: parsed.hash,
    };
  } catch {
    return null;
  }
}

async function listMarks(res, key, limit, defaultHue) {
  const rawMarks = await redisCommand(["LRANGE", key, 0, limit - 1]);
  const marks = Array.isArray(rawMarks) ? rawMarks.map((item) => decodeMark(item, defaultHue)).filter(Boolean).reverse() : [];
  sendJson(res, 200, { marks });
}

async function createMark(res, body, config) {
  await enforceRateLimit(config.ratePrefix, config.rateLimit, config.rateDetail);
  const sequence = coerceInt(await redisCommand(["INCR", config.sequenceKey]), 1);
  const mark = config.fromBody(body, sequence);
  await redisCommand(["LPUSH", config.key, JSON.stringify(mark)]);
  await redisCommand(["LTRIM", config.key, 0, config.limit - 1]);
  sendJson(res, 200, mark);
}

async function createCheckout(res, body) {
  const priceTable = parsePriceTable();
  if (!priceTable) return sendJson(res, 503, { detail: "Billing price table is invalid" });
  const plan = body && body.plan;
  if (plan !== "pro" && plan !== "team") return sendJson(res, 422, { detail: "Invalid plan" });
  const priceId = priceTable[plan];
  if (!priceId) return sendJson(res, 503, { detail: "Billing plan is not configured" });
  const secretKey = (process.env.STRIPE_SECRET_KEY || "").trim();
  if (!secretKey) return sendJson(res, 503, { detail: "Billing checkout is not configured" });

  const params = new URLSearchParams();
  params.set("mode", "subscription");
  params.set("line_items[0][price]", priceId);
  params.set("line_items[0][quantity]", "1");
  params.set("metadata[plan]", plan);
  if (body.customer_email) params.set("customer_email", String(body.customer_email).slice(0, 320));
  if (body.ui_mode === "embedded") {
    params.set("ui_mode", "embedded");
    params.set("return_url", safeReturnUrl(body.success_url, "/success/"));
  } else {
    params.set("success_url", safeReturnUrl(body.success_url, "/success/"));
    params.set("cancel_url", safeReturnUrl(body.cancel_url, "/cancel/"));
  }

  const response = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secretKey}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params.toString(),
  });
  if (!response.ok) return sendJson(res, 502, { detail: "Billing checkout is unavailable" });
  const session = await response.json();
  sendJson(res, 200, {
    client_secret: session.client_secret || null,
    session_id: session.id,
    url: session.url,
  });
}

function routeFromRequest(req) {
  const url = new URL(req.url, "https://cortexpersist.com");
  return url.pathname.replace(/^\/api\/v1\/?/, "").replace(/^\/v1\/?/, "").replace(/\/$/, "");
}

export async function handleRoute(req, res, routeOverride) {
  setCors(req, res);
  if (req.method === "OPTIONS") return sendJson(res, 204, {});
  const route = routeOverride || routeFromRequest(req);
  const url = new URL(req.url, "https://cortexpersist.com");
  const limit = Math.max(1, Math.min(coerceInt(url.searchParams.get("limit"), 96), PROOF_MARK_LIMIT));
  const mediaLimit = Math.max(1, Math.min(coerceInt(url.searchParams.get("limit"), 120), MEDIA_MARK_LIMIT));

  try {
    if ((route === "" || route === "health") && req.method === "GET") {
      return sendJson(res, 200, { service: "cortex-saas-api", status: "ok" });
    }
    if (route === "readiness" && req.method === "GET") {
      return sendJson(res, 200, readinessPayload());
    }
    if (route === "proof-marks" && req.method === "GET") {
      return await listMarks(res, PROOF_MARK_KEY, limit, PROOF_MARK_HUES[0]);
    }
    if (route === "proof-marks" && req.method === "POST") {
      return await createMark(res, await readJsonBody(req), {
        key: PROOF_MARK_KEY,
        sequenceKey: PROOF_MARK_SEQUENCE_KEY,
        ratePrefix: PROOF_MARK_RATE_PREFIX,
        rateLimit: boundedRateLimit("CORTEX_PROOF_MARKS_PER_MINUTE", PROOF_MARK_RATE_LIMIT, 600),
        rateDetail: "Proof mark rate limit exceeded",
        limit: PROOF_MARK_LIMIT,
        fromBody: proofMarkFromBody,
      });
    }
    if (route === "media/marks" && req.method === "GET") {
      return await listMarks(res, MEDIA_MARK_KEY, mediaLimit, MEDIA_MARK_HUES[0]);
    }
    if (route === "media/marks" && req.method === "POST") {
      return await createMark(res, await readJsonBody(req), {
        key: MEDIA_MARK_KEY,
        sequenceKey: MEDIA_MARK_SEQUENCE_KEY,
        ratePrefix: MEDIA_MARK_RATE_PREFIX,
        rateLimit: boundedRateLimit("MEDIA_MARKS_PER_MINUTE", MEDIA_MARK_RATE_LIMIT, 900),
        rateDetail: "Media mark rate limit exceeded",
        limit: MEDIA_MARK_LIMIT,
        fromBody: mediaMarkFromBody,
      });
    }
    if (route === "billing/checkout" && req.method === "POST") {
      return await createCheckout(res, await readJsonBody(req));
    }
    return sendJson(res, 404, { detail: "Not found" });
  } catch (error) {
    return sendJson(res, error.statusCode || 500, { detail: error.message || "API unavailable" });
  }
}

export default handleRoute;
