import { Hono } from "hono";
import { redis, checkRedis } from "../services/redis.js";

const health = new Hono();

health.get("/health", async (c) => {
  const ok = await checkRedis();
  return c.json({
    status: ok ? "ok" : "degraded",
    redis: ok ? "connected" : redis.status,
  }, ok ? 200 : 503);
});

health.get("/ready", async (c) => {
  const ok = await checkRedis();
  return c.json({ ready: ok, redis: redis.status }, ok ? 200 : 503);
});

export { health };
