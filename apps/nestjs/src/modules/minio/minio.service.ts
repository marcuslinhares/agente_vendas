import { Injectable, Logger } from '@nestjs/common';
import { S3Client, PutObjectCommand, ListBucketsCommand } from '@aws-sdk/client-s3';

@Injectable()
export class MinioService {
  private readonly logger = new Logger(MinioService.name);
  private client: S3Client;

  constructor() {
    this.client = new S3Client({
      endpoint: `http://${process.env.MINIO_ENDPOINT || 'localhost:9000'}`,
      region: 'us-east-1',
      credentials: {
        accessKeyId: process.env.MINIO_ACCESS_KEY || 'minioadmin',
        secretAccessKey: process.env.MINIO_SECRET_KEY || 'minioadmin',
      },
      forcePathStyle: true,
    });
  }

  async uploadProductImage(
    productId: string,
    fileName: string,
    buffer: Buffer,
    contentType: string,
  ): Promise<string> {
    const ext = fileName.split('.').pop() || 'webp';
    const key = `${productId}/${Date.now()}.${ext}`;

    await this.client.send(new PutObjectCommand({
      Bucket: 'products',
      Key: key,
      Body: buffer,
      ContentType: contentType,
    }));

    const url = `http://${process.env.MINIO_ENDPOINT || 'localhost:9000'}/products/${key}`;
    this.logger.log(`Uploaded product image: ${url}`);
    return url;
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.client.send(new ListBucketsCommand({}));
      return true;
    } catch {
      return false;
    }
  }
}
