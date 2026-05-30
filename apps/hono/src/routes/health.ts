import { Hono } from "hono";
import { redis } from "../services/redis.js";

const health = new Hono();

health.get("/health", async (c) => {
  try {
    await redis.ping();
    return c.json({ status: "ok", redis: "connected" });
  } catch {
    return c.json({ status: "error", redis: "disconnected" }, 503);
  }
});

health.get("/ready", async (c) => {
  try {
    await redis.ping();
    return c.json({ ready: true });
  } catch {
    return c.json({ ready: false }, 503);
  }
});

export { health };
