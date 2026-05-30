import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import Redis from 'ioredis';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Message, Conversation, MessageEmbedding, Customer } from '../entities';

/** Converts a flat alternating key-value array to a record. */
function fieldsToRecord(fields: string[]): Record<string, string> {
  const record: Record<string, string> = {};
  for (let i = 0; i < fields.length; i += 2) {
    record[fields[i]] = fields[i + 1];
  }
  return record;
}

@Injectable()
export class PersistConsumer implements OnModuleInit {
  private readonly logger = new Logger(PersistConsumer.name);
  private redis: Redis;

  constructor(
    @InjectRepository(Message)
    private readonly msgRepo: Repository<Message>,
    @InjectRepository(Conversation)
    private readonly convRepo: Repository<Conversation>,
    @InjectRepository(MessageEmbedding)
    private readonly embRepo: Repository<MessageEmbedding>,
    @InjectRepository(Customer)
    private readonly custRepo: Repository<Customer>,
  ) {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async onModuleInit(): Promise<void> {
    await this.ensureGroup();
    this.startConsumer();
  }

  private async ensureGroup(): Promise<void> {
    const group = 'nestjs-workers';
    const stream = 'message:persist';
    try {
      await this.redis.xgroup('CREATE', stream, group, '$', 'MKSTREAM');
    } catch (e: any) {
      if (!e.message?.includes('BUSYGROUP')) throw e;
    }
  }

  private startConsumer(): void {
    const group = 'nestjs-workers';
    const stream = 'message:persist';
    const consumer = `consumer-${Date.now()}`;

    this.logger.log(`Listening to ${stream} as ${consumer}`);

    setInterval(async () => {
      try {
        const result = await this.redis.xreadgroup(
          'GROUP', group, consumer,
          'COUNT', 5,
          'BLOCK', 2000,
          'STREAMS', stream, '>',
        ) as [string, [string, string[]][]][] | null;
        if (!result) return;

        for (const [, messages] of result) {
          for (const [msgId, fields] of messages) {
            const record = fieldsToRecord(fields);
            await this.processMessage(msgId, JSON.parse(record['payload']));
            await this.redis.xack(stream, group, msgId);
          }
        }
      } catch (err) {
        this.logger.error('Consumer error', err);
      }
    }, 1000);
  }

  private async processMessage(msgId: string, payload: any): Promise<void> {
    // Idempotency check
    const exists = await this.msgRepo.findOne({
      where: { messageId: payload.id },
    });
    if (exists) {
      this.logger.debug(`Skipping duplicate message ${payload.id}`);
      return;
    }

    // Save message
    const message = this.msgRepo.create({
      messageId: payload.id,
      conversationId: payload.conversation_id,
      role: payload.role,
      content: payload.content,
      mediaUrl: payload.media_url,
      mediaType: payload.media_type,
      metadata: payload.metadata || {},
    });
    await this.msgRepo.save(message);

    // Save embedding if provided (stored as JSON string in TEXT column)
    if (payload.embedding_clip || payload.embedding_text) {
      try {
        const emb = this.embRepo.create({
          conversationId: payload.conversation_id,
          messageId: message.id,
          content: payload.content,
          mediaUrl: payload.media_url,
          embedding: payload.embedding_text
            ? JSON.stringify(payload.embedding_text)
            : undefined,
          embeddingClip: payload.embedding_clip
            ? JSON.stringify(payload.embedding_clip)
            : undefined,
        });
        await this.embRepo.save(emb);
      } catch (err) {
        this.logger.warn(`Failed to save embedding for ${payload.id}: ${err}`);
      }
    }

    // Update customer's last_contact_at
    if (payload.whatsapp_id) {
      try {
        await this.custRepo.update(
          { whatsappId: payload.whatsapp_id },
          { lastContactAt: new Date() },
        );
      } catch {
        // Customer may not exist yet
      }
    }

    // Update conversation message_count
    if (payload.conversation_id) {
      await this.convRepo.increment(
        { id: payload.conversation_id },
        'messageCount',
        1,
      );
    }

    this.logger.debug(`Processed message ${payload.id}`);
  }
}
