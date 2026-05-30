import { z } from "zod";

export const WebhookIncomingSchema = z.object({
  id: z.string().ulid(),
  whatsapp_id: z.string(),
  message: z.string(),
  media_url: z.string().optional(),
  media_type: z.enum(["image", "audio", "video", "document"]).optional(),
  timestamp: z.string().datetime(),
});

export type WebhookIncoming = z.infer<typeof WebhookIncomingSchema>;

export const WhatsAppOutboxSchema = z.object({
  id: z.string().ulid(),
  to: z.string(),
  text: z.string(),
  media_url: z.string().optional(),
});

export type WhatsAppOutbox = z.infer<typeof WhatsAppOutboxSchema>;
