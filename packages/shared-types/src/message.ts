import { z } from "zod";

export const MessagePersistSchema = z.object({
  id: z.string().ulid(),
  conversation_id: z.string().uuid(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  media_url: z.string().optional(),
  media_type: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
  embedding_clip: z.array(z.number()).optional(),
  embedding_text: z.array(z.number()).optional(),
  update_summary: z.boolean().default(false),
});

export type MessagePersist = z.infer<typeof MessagePersistSchema>;
