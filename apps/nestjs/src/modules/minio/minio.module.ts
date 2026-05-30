import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { MinioController } from './minio.controller';
import { MinioService } from './minio.service';
import { Product } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Product])],
  controllers: [MinioController],
  providers: [MinioService],
  exports: [MinioService],
})
export class MinioModule {}
