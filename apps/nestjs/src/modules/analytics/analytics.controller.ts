import { Controller, Get, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Conversation, Message, ToolExecutionLog } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@Controller('analytics')
@UseGuards(JwtAuthGuard)
export class AnalyticsController {
  constructor(
    @InjectRepository(Conversation)
    private readonly convRepo: Repository<Conversation>,
    @InjectRepository(Message)
    private readonly msgRepo: Repository<Message>,
    @InjectRepository(ToolExecutionLog)
    private readonly toolRepo: Repository<ToolExecutionLog>,
  ) {}

  @Get('overview')
  async overview() {
    const totalConversations = await this.convRepo.count();
    const activeConversations = await this.convRepo.count({ where: { status: 'active' } });
    const totalMessages = await this.msgRepo.count();
    const totalToolCalls = await this.toolRepo.count();

    const byClassification = await this.convRepo
      .createQueryBuilder('c')
      .select('c.classification', 'classification')
      .addSelect('COUNT(*)', 'count')
      .where('c.classification IS NOT NULL')
      .groupBy('c.classification')
      .getRawMany();

    const byStatus = await this.convRepo
      .createQueryBuilder('c')
      .select('c.status', 'status')
      .addSelect('COUNT(*)', 'count')
      .groupBy('c.status')
      .getRawMany();

    const toolsUsed = await this.toolRepo
      .createQueryBuilder('t')
      .select('t.toolName', 'tool')
      .addSelect('COUNT(*)', 'count')
      .groupBy('t.toolName')
      .orderBy('COUNT(*)', 'DESC')
      .limit(10)
      .getRawMany();

    return {
      conversations: { total: totalConversations, active: activeConversations },
      messages: totalMessages,
      toolCalls: totalToolCalls,
      byClassification,
      byStatus,
      topTools: toolsUsed,
    };
  }
}
