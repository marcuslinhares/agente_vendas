import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { webhook } from "./routes/webhook.js";
import { health } from "./routes/health.js";
import {
  ensureOutboxGroup,
  consumeOutbox,
  ackOutbox,
  nackOutbox,
} from "./services/redis.js";
import { sendMessage } from "./services/evolution.js";

const app = new Hono();
app.route("/", webhook);
app.route("/", health);

async function startOutboxConsumer(): Promise<void> {
  await ensureOutboxGroup();

  setInterval(async () => {
    try {
      const generator = consumeOutbox();
      for await (const { id, payload } of generator) {
        try {
          await sendMessage(payload.to, payload.text, payload.media_url);
          await ackOutbox(id);
        } catch (err) {
          console.error(`[outbox] Failed to send message ${id}:`, err);
          await nackOutbox(id);
        }
      }
    } catch (err) {
      console.error("[outbox] Consumer error:", err);
    }
  }, 1000);
}

const PORT = parseInt(process.env.HONO_PORT || "3000", 10);

// REQUIRED: Webhook secret must be configured
if (!process.env.EVOLUTION_WEBHOOK_SECRET) {
  console.error("❌ EVOLUTION_WEBHOOK_SECRET is required but not set");
  process.exit(1);
}

// REQUIRED: Evolution API URL must be configured
if (!process.env.EVOLUTION_API_URL) {
  console.error("❌ EVOLUTION_API_URL is required but not set");
  process.exit(1);
}

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`✅ Hono server running on port ${PORT}`);
  startOutboxConsumer().catch(console.error);
});
