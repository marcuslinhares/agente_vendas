import { Controller, Post, UploadedFile, UseGuards, UseInterceptors, Param } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { MinioService } from './minio.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Product } from '../../entities';

@Controller('upload')
@UseGuards(JwtAuthGuard)
export class MinioController {
  constructor(
    private readonly minioService: MinioService,
    @InjectRepository(Product)
    private readonly productRepo: Repository<Product>,
  ) {}

  @Post('product/:productId')
  @UseInterceptors(FileInterceptor('file'))
  async uploadProductImage(
    @Param('productId') productId: string,
    @UploadedFile() file: any,
  ) {
    if (!file) return { error: 'No file provided' };

    const url = await this.minioService.uploadProductImage(
      productId,
      file.originalname,
      file.buffer,
      file.mimetype,
    );

    await this.productRepo.update(productId, { imageUrl: url });
    return { ok: true, imageUrl: url };
  }
}
