import { Hono } from "hono";
import { ulid } from "ulid";
import { publishWebhook } from "../services/redis.js";
import { uploadMedia } from "../services/minio.js";
import { downloadMedia, verifyWebhook } from "../services/evolution.js";

const webhook = new Hono();

webhook.post("/webhook/evolution", async (c) => {
  const signature = c.req.header("x-evolution-signature");
  const body = await c.req.text();

  // REQUIRED: Webhook signature verification
  if (!signature) {
    return c.json({ error: "missing signature header" }, 401);
  }
  try {
    const valid = await verifyWebhook(signature, body);
    if (!valid) {
      return c.json({ error: "invalid signature" }, 401);
    }
  } catch {
    return c.json({ error: "signature verification failed" }, 401);
  }

  let data: any;
  try {
    data = JSON.parse(body);
  } catch {
    return c.json({ error: "invalid JSON body" }, 400);
  }

  const whatsappId = data.key?.remoteJid || data.from;
  if (!whatsappId) {
    return c.json({ error: "missing sender identifier" }, 400);
  }

  const messageText =
    data.message?.conversation ||
    data.message?.extendedTextMessage?.text ||
    "";

  const mediaInfo = extractMedia(data.message);

  let mediaUrl: string | undefined;
  let mediaType: string | undefined;

  if (mediaInfo) {
    try {
      const raw = await downloadMedia(mediaInfo.url);
      const extMap: Record<string, string> = {
        image: "jpg",
        audio: "ogg",
        video: "mp4",
        document: "pdf",
      };
      const ext = extMap[mediaInfo.type] || "bin";
      const key = `${whatsappId}/${ulid()}.${ext}`;
      mediaUrl = await uploadMedia("conversations-media", key, raw, mediaInfo.mimeType);
      mediaType = mediaInfo.type;
    } catch (err) {
      console.error(`[webhook] Media download/upload failed:`, err);
      // Continue without media URL — agent can still process text
    }
  }

  const streamId = await publishWebhook({
    id: ulid(),
    whatsapp_id: whatsappId,
    message: messageText,
    media_url: mediaUrl,
    media_type: mediaType,
    timestamp: new Date().toISOString(),
  });

  return c.json({ ok: true, stream_id: streamId });
});

function extractMedia(
  msg: any
): { url: string; type: string; mimeType: string } | null {
  if (!msg) return null;
  const image = msg.imageMessage;
  if (image) {
    return { url: image.url, type: "image", mimeType: image.mimetype || "image/jpeg" };
  }
  const audio = msg.audioMessage;
  if (audio) {
    return { url: audio.url, type: "audio", mimeType: audio.mimetype || "audio/ogg" };
  }
  const video = msg.videoMessage;
  if (video) {
    return { url: video.url, type: "video", mimeType: video.mimetype || "video/mp4" };
  }
  const doc = msg.documentMessage;
  if (doc) {
    return { url: doc.url, type: "document", mimeType: doc.mimetype || "application/octet-stream" };
  }
  return null;
}

export { webhook };
