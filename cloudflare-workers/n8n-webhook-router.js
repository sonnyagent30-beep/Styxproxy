// Styxproxy n8n Webhook Router — Cloudflare Worker
// Rewrites incoming webhook requests to match n8n 1.123.x URL pattern
//
// Pattern needed by n8n 1.123.x:
//   /webhook/<workflowId>/<node-name-slug>/<path>
//
// What Flutterwave/WhatsApp/Telegram currently call:
//   /webhook/<path>          (legacy n8n format, <1.0)
//
// What we do:
//   1. Receive POST /webhook/<path>
//   2. Look up <path> in KV to find {workflowId, nodeSlug}
//   3. Rewrite to /webhook/<workflowId>/<nodeSlug>/<path>
//   4. Forward to origin
//
// If <path> isn't in KV, return 404 immediately (don't leak to origin).
// If KV lookup fails (timeout), fall through to origin with original URL.

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Only handle /webhook/ paths; let everything else through
    if (!url.pathname.startsWith("/webhook/")) {
      return fetch(request);
    }

    // Extract the webhook path: /webhook/<X> where X is everything after
    const webhookPath = url.pathname.slice("/webhook/".length);
    if (!webhookPath) {
      return new Response("Bad webhook path", { status: 400 });
    }

    // Look up the routing entry in KV
    // Key format: webhook:<X>
    // Value format: { workflowId, nodeSlug, methodsAllowed }
    let kvKey = `webhook:${webhookPath}`;
    let entry = null;
    try {
      entry = await env.N8N_WEBHOOK_MAP.get(kvKey, "json");
    } catch (e) {
      // KV failure — fall through to origin with original URL
      // Better than dropping requests on a KV outage
      console.error("KV lookup failed for", kvKey, e);
      return fetch(request);
    }

    if (!entry) {
      return new Response(
        JSON.stringify({
          code: 404,
          message: `Webhook '${webhookPath}' not registered`,
        }),
        {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Method check
    if (entry.methodsAllowed && !entry.methodsAllowed.includes(request.method)) {
      return new Response("Method not allowed", {
        status: 405,
        headers: { Allow: entry.methodsAllowed.join(", ") },
      });
    }

    // Rewrite URL: /webhook/<X> → /webhook/<workflowId>/<nodeSlug>/<X>
    const newPath = `/webhook/${entry.workflowId}/${entry.nodeSlug}/${webhookPath}`;
    url.pathname = newPath;

    // Add diagnostic header so we can see the rewrite happened
    const modifiedRequest = new Request(url.toString(), request);
    modifiedRequest.headers.set("X-Styxproxy-Rewritten", "true");
    modifiedRequest.headers.set("X-Styxproxy-Original-Path", webhookPath);

    // Forward to origin (n8n)
    return fetch(modifiedRequest, {
      // Don't cache webhook responses
      cf: { cacheTtl: 0, cacheEverything: false },
    });
  },

  // Scheduled handler — sync n8n webhook DB → KV every 5 min
  // Cron: every 5 minutes
  async scheduled(event, env, ctx) {
    ctx.waitUntil(syncWebhookMap(env));
  },
};

async function syncWebhookMap(env) {
  // Query n8n Postgres for all registered webhooks
  // n8n stores them in n8n_webhook_entity table
  const query = `
    SELECT
      we.name AS workflow_name,
      n.id AS workflow_id,
      wh.webhookPath,
      wh.method,
      n.name AS node_name
    FROM n8n_webhook_entity wh
    JOIN n8n_workflow_entity we ON we.id = wh."workflowId"
    JOIN LATERAL (
      SELECT id, name
      FROM jsonb_array_elements(we.nodes::jsonb) AS n
      WHERE n->>'type' = 'n8n-nodes-base.webhook'
      LIMIT 1
    ) n ON true
    WHERE we.active = true
  `;

  // Use the Postgres HTTP Data API (Supabase-compatible endpoint)
  // OR use a tiny API endpoint in charon that exposes this query
  // For now, expect charon to expose GET /admin/internal/webhooks

  const apiUrl = `${env.CHARON_INTERNAL_URL}/admin/internal/webhooks`;
  const authHeader = `Bearer ${env.CHARON_INTERNAL_KEY}`;

  try {
    const resp = await fetch(apiUrl, {
      headers: { Authorization: authHeader },
    });
    if (!resp.ok) {
      console.error("Failed to fetch webhook list:", resp.status);
      return;
    }
    const webhooks = await resp.json();

    // Rebuild KV: write each entry, then clear stale ones
    const seenKeys = new Set();
    for (const wh of webhooks) {
      // n8n stores path as URL-encoded workflowId/nodeSlug/path
      // We need to reverse-extract just the <path> part
      // Path format: "<workflowId>/<node-slug>/<actual-path>"
      const parts = wh.webhookPath.split("/");
      if (parts.length < 3) continue;

      const workflowId = parts[0];
      const actualPath = parts.slice(2).join("/");
      const nodeSlug = parts[1];

      const kvKey = `webhook:${actualPath}`;
      const value = JSON.stringify({
        workflowId,
        nodeSlug,
        methodsAllowed: [wh.method],
      });

      await env.N8N_WEBHOOK_MAP.put(kvKey, value);
      seenKeys.add(kvKey);
    }

    // (Optional) clear stale entries by listing all `webhook:*` keys
    // and deleting ones not in seenKeys. KV doesn't support "delete by
    // prefix" cleanly — for now, rely on TTL or accept some staleness.

    console.log(`Synced ${seenKeys.size} webhooks to KV`);
  } catch (e) {
    console.error("Webhook sync failed:", e);
  }
}
