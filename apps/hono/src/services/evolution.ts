const EVOLUTION_API_URL = process.env.EVOLUTION_API_URL || "";
const EVOLUTION_API_KEY = process.env.EVOLUTION_API_KEY || "";

export async function sendMessage(to: string, text: string, mediaUrl?: string): Promise<void> {
  const body: Record<string, unknown> = { number: to, text };
  if (mediaUrl) body.mediaUrl = mediaUrl;

  const res = await fetch(`${EVOLUTION_API_URL}/message/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apiKey: EVOLUTION_API_KEY,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(`Evolution API error: ${res.status} ${await res.text()}`);
  }
}

export async function downloadMedia(mediaUrl: string): Promise<Buffer> {
  const res = await fetch(mediaUrl, {
    headers: { apiKey: EVOLUTION_API_KEY },
  });
  if (!res.ok) {
    throw new Error(`Failed to download media: ${res.status}`);
  }
  const arrayBuffer = await res.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

export async function verifyWebhook(signature: string, body: string): Promise<boolean> {
  const secret = process.env.EVOLUTION_WEBHOOK_SECRET || "";
  const crypto = await import("crypto");
  const expected = crypto.createHmac("sha256", secret).update(body).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
