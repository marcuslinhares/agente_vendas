import { Controller, Get, Param, Query } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Message } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { UseGuards } from '@nestjs/common';

@Controller('messages')
@UseGuards(JwtAuthGuard)
export class MessagesController {
  constructor(
    @InjectRepository(Message)
    private readonly msgRepo: Repository<Message>,
  ) {}

  @Get(':conversationId')
  async findByConversation(
    @Param('conversationId') conversationId: string,
    @Query('offset') offset = 0,
    @Query('limit') limit = 50,
  ) {
    const [messages, total] = await this.msgRepo.findAndCount({
      where: { conversationId },
      order: { createdAt: 'DESC' },
      skip: offset,
      take: limit,
    });
    return { messages, total, offset, limit };
  }
}
