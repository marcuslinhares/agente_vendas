import { Controller, Get, Param, Query, Post, Body, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Conversation, Message } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import Redis from 'ioredis';
import { ulid } from 'ulid';
import { IsOptional, IsString } from 'class-validator';

class ListConversationsQuery {
  @IsOptional()
  @IsString()
  status?: string;

  @IsOptional()
  @IsString()
  classification?: string;

  @IsOptional()
  @IsString()
  search?: string;
}

class SendMessageDto {
  @IsString()
  text!: string;

  @IsOptional()
  @IsString()
  mediaUrl?: string;
}

@Controller('conversations')
@UseGuards(JwtAuthGuard)
export class ConversationsController {
  private redis: Redis;

  constructor(
    @InjectRepository(Conversation)
    private readonly convRepo: Repository<Conversation>,
    @InjectRepository(Message)
    private readonly msgRepo: Repository<Message>,
  ) {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  @Get()
  async list(@Query() query: ListConversationsQuery) {
    const qb = this.convRepo.createQueryBuilder('c')
      .orderBy('c.updatedAt', 'DESC');

    if (query.status) {
      qb.andWhere('c.status = :status', { status: query.status });
    }
    if (query.classification) {
      qb.andWhere('c.classification = :classification', { classification: query.classification });
    }
    if (query.search) {
      qb.andWhere('c.whatsappId ILIKE :search', { search: `%${query.search}%` });
    }

    return qb.getMany();
  }

  @Get(':id')
  async get(@Param('id') id: string) {
    const conversation = await this.convRepo.findOne({ where: { id } });
    const messages = await this.msgRepo.find({
      where: { conversationId: id },
      order: { createdAt: 'DESC' },
      take: 50,
    });
    return { ...conversation, messages };
  }

  @Post(':id/send')
  async send(@Param('id') id: string, @Body() dto: SendMessageDto) {
    const conversation = await this.convRepo.findOne({ where: { id } });
    if (!conversation) {
      return { error: 'Conversation not found' };
    }

    await this.redis.xadd('whatsapp:outbox', '*', 'payload', JSON.stringify({
      id: ulid(),
      to: conversation.whatsappId,
      text: dto.text,
      media_url: dto.mediaUrl,
    }));

    return { ok: true, message: 'Message sent to outbox' };
  }
}
