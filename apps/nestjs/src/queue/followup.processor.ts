import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';
import { Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Customer } from '../entities';
import Redis from 'ioredis';
import { ulid } from 'ulid';

@Processor('followup')
export class FollowupProcessor extends WorkerHost {
  private readonly logger = new Logger(FollowupProcessor.name);
  private redis: Redis;

  constructor(
    @InjectRepository(Customer)
    private readonly custRepo: Repository<Customer>,
  ) {
    super();
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async process(job: Job): Promise<void> {
    this.logger.log(`Running follow-up check (job ${job.id})`);

    const threeDaysAgo = new Date();
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

    // Find lead_morno customers without contact > 3 days
    const customers = await this.custRepo.find({
      where: { classification: 'lead_morno' },
    });

    if (customers.length === 0) {
      this.logger.log('Follow-up: no lead_morno customers found');
      return;
    }

    let sent = 0;
    for (const customer of customers) {
      if (!customer.lastContactAt || customer.lastContactAt < threeDaysAgo) {
        await this.redis.xadd('whatsapp:outbox', '*', 'payload', JSON.stringify({
          id: ulid(),
          to: customer.whatsappId,
          text: 'Olá! Passando pra saber se você ainda tem interesse em nossos produtos. Posso ajudar?',
        }));
        sent++;
      }
    }

    this.logger.log(`Follow-up: ${sent} messages sent`);
  }
}
