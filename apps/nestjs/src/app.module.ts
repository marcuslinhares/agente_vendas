import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BullModule } from '@nestjs/bullmq';
import { entities } from './entities';
import { StreamModule } from './stream/stream.module';
import { AuthModule } from './modules/auth/auth.module';
import { ConversationsModule } from './modules/conversations/conversations.module';
import { MessagesModule } from './modules/messages/messages.module';
import { ProductsModule } from './modules/products/products.module';
import { CustomersModule } from './modules/customers/customers.module';
import { OrdersModule } from './modules/orders/orders.module';
import { ToolsModule } from './modules/tools/tools.module';
import { MinioModule } from './modules/minio/minio.module';
import { QueueModule } from './queue/queue.module';

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
    ProductsModule,
    CustomersModule,
    OrdersModule,
    ToolsModule,
    MinioModule,
    QueueModule,
    StreamModule,
  ],
  controllers: [],
  providers: [],
})
export class AppModule {}
