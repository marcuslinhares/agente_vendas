import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { MessagesController } from './messages.controller';
import { Message } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Message])],
  controllers: [MessagesController],
})
export class MessagesModule {}
