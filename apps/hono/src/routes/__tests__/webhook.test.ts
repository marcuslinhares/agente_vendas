import { describe, it, expect, vi, beforeEach } from "vitest";
import { webhook } from "../webhook.js";

// Mock the services used by webhook route
vi.mock("../../services/evolution.js", () => ({
  verifyWebhook: vi.fn(),
  downloadMedia: vi.fn(),
}));

vi.mock("../../services/redis.js", () => ({
  publishWebhook: vi.fn(),
}));

vi.mock("../../services/minio.js", () => ({
  uploadMedia: vi.fn(),
}));

import { verifyWebhook } from "../../services/evolution.js";

describe("Webhook Route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("POST /webhook/evolution", () => {
    it("returns 401 when signature header is missing", async () => {
      const res = await webhook.request("/webhook/evolution", {
        method: "POST",
        body: JSON.stringify({ test: true }),
      });

      expect(res.status).toBe(401);
      const data = await res.json();
      expect(data).toEqual({ error: "missing signature header" });
    });

    it("returns 401 when signature verification throws an error", async () => {
      // Mock verifyWebhook to throw an error, hitting the catch block
      (verifyWebhook as any).mockRejectedValueOnce(new Error("Verification failed"));

      const res = await webhook.request("/webhook/evolution", {
        method: "POST",
        headers: {
          "x-evolution-signature": "invalid-signature",
        },
        body: JSON.stringify({ test: true }),
      });

      expect(res.status).toBe(401);
      const data = await res.json();
      expect(data).toEqual({ error: "Invalid signature" });
    });

    it("returns 401 when signature is invalid (valid === false)", async () => {
      // Mock verifyWebhook to return false
      (verifyWebhook as any).mockResolvedValueOnce(false);

      const res = await webhook.request("/webhook/evolution", {
        method: "POST",
        headers: {
          "x-evolution-signature": "invalid-signature",
        },
        body: JSON.stringify({ test: true }),
      });

      expect(res.status).toBe(401);
      const data = await res.json();
      expect(data).toEqual({ error: "Invalid signature" });
    });

    it("returns 400 when body is invalid JSON", async () => {
      // Mock verifyWebhook to return true
      (verifyWebhook as any).mockResolvedValueOnce(true);

      const res = await webhook.request("/webhook/evolution", {
        method: "POST",
        headers: {
          "x-evolution-signature": "valid-signature",
        },
        body: "invalid-json",
      });

      expect(res.status).toBe(400);
      const data = await res.json();
      expect(data).toEqual({ error: "invalid JSON body" });
    });
  });
});
