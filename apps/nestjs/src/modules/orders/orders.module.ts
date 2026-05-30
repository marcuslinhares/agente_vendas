import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { OrdersController } from './orders.controller';
import { Order } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Order])],
  controllers: [OrdersController],
})
export class OrdersModule {}
