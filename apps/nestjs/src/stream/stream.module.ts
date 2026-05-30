import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PersistConsumer } from './persist.consumer';
import { Message, Conversation, MessageEmbedding, Customer } from '../entities';

@Module({
  imports: [
    TypeOrmModule.forFeature([Message, Conversation, MessageEmbedding, Customer]),
  ],
  providers: [PersistConsumer],
})
export class StreamModule {}
