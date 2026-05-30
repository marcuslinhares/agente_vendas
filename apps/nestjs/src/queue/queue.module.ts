import { Module, Logger } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BullModule } from '@nestjs/bullmq';
import { FollowupProcessor } from './followup.processor';
import { ReindexProcessor } from './reindex.processor';
import { Customer, Conversation, Product, ProductEmbedding } from '../entities';

@Module({
  imports: [
    TypeOrmModule.forFeature([Customer, Conversation, Product, ProductEmbedding]),
    BullModule.registerQueue(
      { name: 'followup' },
      { name: 'reindex' },
    ),
  ],
  providers: [FollowupProcessor, ReindexProcessor],
})
export class QueueModule {
  private readonly logger = new Logger(QueueModule.name);

  constructor() {
    this.setupSchedule().catch((err) =>
      this.logger.error('Failed to set up repeatable job schedules', err),
    );
  }

  private async setupSchedule(): Promise<void> {
    const { Queue } = await import('bullmq');
    const host = process.env.REDIS_URL?.replace('redis://', '')?.split(':')[0] || 'localhost';
    const port = parseInt(process.env.REDIS_URL?.split(':')[2] || '6379', 10);
    const connection = { host, port };

    // Follow-up runs daily at 9:00 AM
    const followupQueue = new Queue('followup', { connection });
    await followupQueue.upsertJobScheduler(
      'daily-followup',
      { pattern: '0 9 * * *' },
      { name: 'daily-followup-check' },
    );

    // Reindex runs nightly at 2:00 AM
    const reindexQueue = new Queue('reindex', { connection });
    await reindexQueue.upsertJobScheduler(
      'nightly-reindex',
      { pattern: '0 2 * * *' },
      { name: 'product-reindex' },
    );

    this.logger.log('BullMQ repeatable job schedules registered');
  }
}
