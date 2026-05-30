import Redis from "ioredis";

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";
const STREAM_WEBHOOK = "webhook:incoming";
const STREAM_OUTBOX = "whatsapp:outbox";
const OUTBOX_GROUP = "hono-workers";

export const redis = new Redis(REDIS_URL, {
  enableOfflineQueue: false,
  maxRetriesPerRequest: 3,
});

// Expose a ping helper that doesn't hang
export async function checkRedis(): Promise<boolean> {
  try {
    await redis.ping();
    return true;
  } catch {
    return false;
  }
}

export async function ensureOutboxGroup(): Promise<void> {
  try {
    void await redis.xgroup("CREATE", STREAM_OUTBOX, OUTBOX_GROUP, "$", "MKSTREAM");
  } catch (e: any) {
    if (!e.message?.includes("BUSYGROUP")) throw e;
  }
}

export async function publishWebhook(payload: Record<string, unknown>): Promise<string> {
  const id = await redis.xadd(STREAM_WEBHOOK, "*", "payload", JSON.stringify(payload));
  if (!id) throw new Error("publishWebhook: xadd returned null");
  return id;
}

type StreamEntry = [string, string[]];

export async function* consumeOutbox(batchSize = 5): AsyncGenerator<{ id: string; payload: any }> {
  const result = await redis.xreadgroup(
    "GROUP", OUTBOX_GROUP, `consumer-${Date.now()}`,
    "COUNT", batchSize,
    "BLOCK", 2000,
    "STREAMS", STREAM_OUTBOX, ">"
  );
  if (!result) return;
  for (const [, messages] of result as [string, StreamEntry[]][]) {
    for (const [id, fields] of messages) {
      const payloadIdx = fields.indexOf("payload");
      if (payloadIdx !== -1 && fields[payloadIdx + 1]) {
        const payload = JSON.parse(fields[payloadIdx + 1]);
        yield { id, payload };
      }
    }
  }
}

export async function ackOutbox(streamId: string): Promise<void> {
  await redis.xack(STREAM_OUTBOX, OUTBOX_GROUP, streamId);
}

export async function nackOutbox(streamId: string): Promise<void> {
  const attempts = await redis.hincrby(`attempts:${streamId}`, "count", 1);
  if (attempts >= 3) {
    await redis.xadd("whatsapp:outbox:deadletter", "*", "stream_id", streamId);
  }
}
