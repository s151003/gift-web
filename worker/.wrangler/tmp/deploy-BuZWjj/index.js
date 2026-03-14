var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/index.ts
var ALLOWED_SITES = ["ama-gift", "giftissue", "beterugift", "amaten"];
function corsHeaders(origin, allowedOrigin) {
  const headers = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
  };
  if (origin && (origin === allowedOrigin || origin.startsWith("http://localhost") || origin.startsWith("http://127.0.0.1"))) {
    headers["Access-Control-Allow-Origin"] = origin;
  } else {
    headers["Access-Control-Allow-Origin"] = allowedOrigin;
  }
  return headers;
}
__name(corsHeaders, "corsHeaders");
function json(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...extraHeaders }
  });
}
__name(json, "json");
function isISO8601UTC(s) {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s);
}
__name(isISO8601UTC, "isISO8601UTC");
function isWithinOneHour(scraped_at) {
  const diff = Math.abs(Date.now() - new Date(scraped_at).getTime());
  return diff <= 60 * 60 * 1e3;
}
__name(isWithinOneHour, "isWithinOneHour");
function validateSnapshot(s) {
  if (typeof s !== "object" || s === null) return false;
  const o = s;
  if (!ALLOWED_SITES.includes(o.site_name)) return false;
  if (!Number.isInteger(o.listing_count) || o.listing_count < 0) return false;
  for (const key of ["best_discount_rate", "worst_discount_rate", "avg_discount_rate", "median_discount_rate"]) {
    const v = o[key];
    if (typeof v !== "number" || v < 0 || v >= 100) return false;
  }
  const best = o.best_discount_rate;
  const avg = o.avg_discount_rate;
  const median = o.median_discount_rate;
  const worst = o.worst_discount_rate;
  if (!(best >= worst)) return false;
  return true;
}
__name(validateSnapshot, "validateSnapshot");
function validateTransaction(t) {
  if (typeof t !== "object" || t === null) return false;
  const o = t;
  if (!ALLOWED_SITES.includes(o.site_name)) return false;
  if (typeof o.traded_at !== "string" || !isISO8601UTC(o.traded_at)) return false;
  if (!Number.isInteger(o.face_value) || o.face_value <= 0) return false;
  if (!Number.isInteger(o.traded_price) || o.traded_price <= 0) return false;
  if (o.traded_price >= o.face_value) return false;
  if (typeof o.discount_rate !== "number" || o.discount_rate < 0 || o.discount_rate >= 100) return false;
  return true;
}
__name(validateTransaction, "validateTransaction");
async function handleIngest(req, env) {
  const auth = req.headers.get("Authorization");
  if (!auth || auth !== `Bearer ${env.INGEST_SECRET_TOKEN}`) {
    return json({ error: "Unauthorized" }, 401);
  }
  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }
  if (typeof body !== "object" || body === null) return json({ error: "Invalid body" }, 400);
  const { scraped_at, snapshots, transactions } = body;
  if (typeof scraped_at !== "string" || !isISO8601UTC(scraped_at)) {
    return json({ error: "scraped_at must be ISO 8601 UTC" }, 400);
  }
  if (!isWithinOneHour(scraped_at)) {
    return json({ error: "scraped_at is too old or in the future (must be within \xB11 hour)" }, 400);
  }
  if (!Array.isArray(snapshots)) return json({ error: "snapshots must be an array" }, 400);
  if (!Array.isArray(transactions)) return json({ error: "transactions must be an array" }, 400);
  for (const s of snapshots) {
    if (!validateSnapshot(s)) return json({ error: "Invalid snapshot data", data: s }, 400);
  }
  for (const t of transactions) {
    if (!validateTransaction(t)) return json({ error: "Invalid transaction data", data: t }, 400);
  }
  try {
    const stmts = [];
    for (const s of snapshots) {
      stmts.push(
        env.DB.prepare(
          `INSERT OR REPLACE INTO price_snapshots
            (site_name, scraped_at, listing_count, best_discount_rate, worst_discount_rate, avg_discount_rate, median_discount_rate)
           VALUES (?, ?, ?, ?, ?, ?, ?)`
        ).bind(
          s.site_name,
          scraped_at,
          s.listing_count,
          s.best_discount_rate,
          s.worst_discount_rate,
          s.avg_discount_rate,
          s.median_discount_rate
        )
      );
    }
    for (const t of transactions) {
      stmts.push(
        env.DB.prepare(
          `INSERT OR IGNORE INTO transactions
            (site_name, traded_at, face_value, traded_price, discount_rate, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?)`
        ).bind(t.site_name, t.traded_at, t.face_value, t.traded_price, t.discount_rate, scraped_at)
      );
    }
    if (stmts.length > 0) {
      await env.DB.batch(stmts);
    }
    return json({ inserted_snapshots: snapshots.length, inserted_transactions: transactions.length });
  } catch (e) {
    console.error(e);
    return json({ error: "DB write failed" }, 500);
  }
}
__name(handleIngest, "handleIngest");
async function handleSnapshotsLatest(env) {
  const result = await env.DB.prepare(
    `SELECT * FROM price_snapshots
     WHERE (site_name, scraped_at) IN (
       SELECT site_name, MAX(scraped_at) FROM price_snapshots GROUP BY site_name
     )
     ORDER BY site_name`
  ).all();
  return json({ data: result.results });
}
__name(handleSnapshotsLatest, "handleSnapshotsLatest");
async function handleSnapshots(req, env) {
  const url = new URL(req.url);
  let hours = parseInt(url.searchParams.get("hours") ?? "24", 10);
  if (isNaN(hours) || hours < 1) hours = 24;
  if (hours > 168) hours = 168;
  const site = url.searchParams.get("site");
  let query;
  let params;
  if (site) {
    if (!ALLOWED_SITES.includes(site)) {
      return json({ error: "Invalid site" }, 400);
    }
    query = `SELECT * FROM price_snapshots
             WHERE site_name = ? AND scraped_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || ? || ' hours')
             ORDER BY scraped_at ASC`;
    params = [site, String(hours)];
  } else {
    query = `SELECT * FROM price_snapshots
             WHERE scraped_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || ? || ' hours')
             ORDER BY scraped_at ASC`;
    params = [String(hours)];
  }
  const result = await env.DB.prepare(query).bind(...params).all();
  return json({ data: result.results });
}
__name(handleSnapshots, "handleSnapshots");
async function handleTransactions(req, env) {
  const url = new URL(req.url);
  const site = url.searchParams.get("site");
  let hours = parseInt(url.searchParams.get("hours") ?? "48", 10);
  let limit = parseInt(url.searchParams.get("limit") ?? "100", 10);
  if (isNaN(hours) || hours < 1) hours = 48;
  if (hours > 168) hours = 168;
  if (isNaN(limit) || limit < 1) limit = 100;
  if (limit > 500) limit = 500;
  let query;
  let params;
  if (site) {
    if (!ALLOWED_SITES.includes(site)) {
      return json({ error: "Invalid site" }, 400);
    }
    query = `SELECT * FROM transactions
             WHERE site_name = ? AND traded_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || ? || ' hours')
             ORDER BY traded_at DESC
             LIMIT ?`;
    params = [site, String(hours), String(limit)];
  } else {
    query = `SELECT * FROM transactions
             WHERE traded_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || ? || ' hours')
             ORDER BY traded_at DESC
             LIMIT ?`;
    params = [String(hours), String(limit)];
  }
  const result = await env.DB.prepare(query).bind(...params).all();
  return json({ data: result.results });
}
__name(handleTransactions, "handleTransactions");
async function handleHealth(env) {
  const result = await env.DB.prepare(
    `SELECT MAX(scraped_at) as latest_scraped_at FROM price_snapshots`
  ).first();
  const latest = result?.latest_scraped_at ?? null;
  let stale = true;
  if (latest) {
    const diff = Date.now() - new Date(latest).getTime();
    stale = diff > 2 * 60 * 60 * 1e3;
  }
  return json({ status: "ok", latest_scraped_at: latest, stale });
}
__name(handleHealth, "handleHealth");
var index_default = {
  async fetch(req, env) {
    const origin = req.headers.get("Origin");
    const cors = corsHeaders(origin, env.FRONTEND_ORIGIN ?? "");
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    const url = new URL(req.url);
    const path = url.pathname;
    let res;
    try {
      if (req.method === "POST" && path === "/api/ingest") {
        res = await handleIngest(req, env);
      } else if (req.method === "GET" && path === "/api/snapshots/latest") {
        res = await handleSnapshotsLatest(env);
      } else if (req.method === "GET" && path === "/api/snapshots") {
        res = await handleSnapshots(req, env);
      } else if (req.method === "GET" && path === "/api/transactions") {
        res = await handleTransactions(req, env);
      } else if (req.method === "GET" && path === "/api/health") {
        res = await handleHealth(env);
      } else {
        res = json({ error: "Not found" }, 404);
      }
    } catch (e) {
      console.error(e);
      res = json({ error: "Internal server error" }, 500);
    }
    const newHeaders = new Headers(res.headers);
    for (const [k, v] of Object.entries(cors)) {
      newHeaders.set(k, v);
    }
    return new Response(res.body, { status: res.status, headers: newHeaders });
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
