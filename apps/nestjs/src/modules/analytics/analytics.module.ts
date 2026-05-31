import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AnalyticsController } from './analytics.controller';
import { Conversation, Message, ToolExecutionLog } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Conversation, Message, ToolExecutionLog])],
  controllers: [AnalyticsController],
})
export class AnalyticsModule {}
