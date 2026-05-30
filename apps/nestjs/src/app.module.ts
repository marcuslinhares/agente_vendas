import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BullModule } from '@nestjs/bullmq';
import { entities } from './entities';
import { StreamModule } from './stream/stream.module';
import { AuthModule } from './modules/auth/auth.module';
import { ConversationsModule } from './modules/conversations/conversations.module';
import { MessagesModule } from './modules/messages/messages.module';

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      url: process.env.DATABASE_URL || 'postgresql://app:localdev@localhost:5432/agentevendas',
      entities,
      synchronize: false,
    }),
    BullModule.forRoot({
      connection: {
        host: process.env.REDIS_URL?.replace('redis://', '')?.split(':')[0] || 'localhost',
        port: parseInt(process.env.REDIS_URL?.split(':')[2] || '6379', 10),
      },
    }),
    AuthModule,
    ConversationsModule,
    MessagesModule,
    StreamModule,
  ],
  controllers: [],
  providers: [],
})
export class AppModule {}
