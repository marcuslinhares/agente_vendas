import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Job } from 'bullmq';
import { Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Product, ProductEmbedding } from '../entities';

@Processor('reindex')
export class ReindexProcessor extends WorkerHost {
  private readonly logger = new Logger(ReindexProcessor.name);

  constructor(
    @InjectRepository(Product)
    private readonly prodRepo: Repository<Product>,
    @InjectRepository(ProductEmbedding)
    private readonly embRepo: Repository<ProductEmbedding>,
  ) {
    super();
  }

  async process(job: Job): Promise<void> {
    this.logger.log('Starting product reindex');

    // Find active products
    const products = await this.prodRepo.find({ where: { isActive: true } });

    if (products.length === 0) {
      this.logger.log('Reindex: no active products found');
      return;
    }

    let indexed = 0;

    for (const product of products) {
      // Check if embedding already exists for this product
      const existing = await this.embRepo.findOne({ where: { productId: product.id } });
      if (!existing) {
        const emb = this.embRepo.create({
          productId: product.id,
          content: `${product.name}: ${product.description || ''}`,
        });
        await this.embRepo.save(emb);
        indexed++;
      }
    }

    this.logger.log(`Reindex complete: ${indexed} products indexed`);
  }
}
