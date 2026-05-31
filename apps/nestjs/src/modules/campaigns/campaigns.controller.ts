import { Controller, Get, Post, Param, Body, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Campaign } from './campaign.entity';
import { Customer } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import Redis from 'ioredis';
import { ulid } from 'ulid';

@Controller('campaigns')
@UseGuards(JwtAuthGuard)
export class CampaignsController {
  private redis: Redis;

  constructor(
    @InjectRepository(Campaign)
    private readonly repo: Repository<Campaign>,
    @InjectRepository(Customer)
    private readonly custRepo: Repository<Customer>,
  ) {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  @Get()
  async list() {
    return this.repo.find({ order: { createdAt: 'DESC' } });
  }

  @Get(':id')
  async get(@Param('id') id: string) {
    return this.repo.findOne({ where: { id } });
  }

  @Post()
  async create(@Body() body: Partial<Campaign>) {
    const campaign = this.repo.create(body);
    return this.repo.save(campaign);
  }

  @Post(':id/send')
  async send(@Param('id') id: string) {
    const campaign = await this.repo.findOne({ where: { id } });
    if (!campaign) return { error: 'Campaign not found' };

    const customers = await this.custRepo.find({
      where: campaign.targetClassification
        ? { classification: campaign.targetClassification }
        : {},
    });

    let sent = 0;
    for (const customer of customers) {
      const message = campaign.messageTemplate || 'Olá!';
      const personalized = message
        .replace('{{nome}}', customer.name || '')
        .replace('{{whatsapp}}', customer.whatsappId || '');

      await this.redis.xadd('whatsapp:outbox', '*', 'payload', JSON.stringify({
        id: ulid(),
        to: customer.whatsappId,
        text: personalized,
      }));
      sent++;
    }

    campaign.sentCount = sent;
    campaign.totalTarget = customers.length;
    campaign.status = 'completed';
    await this.repo.save(campaign);

    return { ok: true, sent, total: customers.length };
  }

  @Post(':id/schedule')
  async schedule(@Param('id') id: string, @Body() body: { scheduledAt: string }) {
    await this.repo.update(id, {
      scheduledAt: new Date(body.scheduledAt),
      status: 'scheduled',
    });
    return { ok: true };
  }
}
