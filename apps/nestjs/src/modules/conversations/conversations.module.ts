import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConversationsController } from './conversations.controller';
import { Conversation, Message } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Conversation, Message])],
  controllers: [ConversationsController],
})
export class ConversationsModule {}
