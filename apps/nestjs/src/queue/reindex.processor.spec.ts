import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { ReindexProcessor } from './reindex.processor';
import { Product, ProductEmbedding } from '../entities';
import { Job } from 'bullmq';
import { S3Client } from '@aws-sdk/client-s3';
import { OpenAI } from 'openai';

jest.mock('@aws-sdk/client-s3', () => ({
  S3Client: jest.fn().mockImplementation(() => ({
    send: jest.fn(),
  })),
  GetObjectCommand: jest.fn(),
}));

jest.mock('openai', () => ({
  OpenAI: jest.fn().mockImplementation(() => ({
    embeddings: {
      create: jest.fn().mockResolvedValue({
        data: [{ embedding: [0.1, 0.2, 0.3] }],
      }),
    },
  })),
}));

describe('ReindexProcessor', () => {
  let processor: ReindexProcessor;
  let prodRepo: any;
  let embRepo: any;

  beforeEach(async () => {
    prodRepo = {
      find: jest.fn(),
    };
    embRepo = {
      findOne: jest.fn(),
      save: jest.fn(),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ReindexProcessor,
        {
          provide: getRepositoryToken(Product),
          useValue: prodRepo,
        },
        {
          provide: getRepositoryToken(ProductEmbedding),
          useValue: embRepo,
        },
      ],
    }).compile();

    processor = module.get<ReindexProcessor>(ReindexProcessor);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should be defined', () => {
    expect(processor).toBeDefined();
  });

  it('should process correctly when no active products are found', async () => {
    prodRepo.find.mockResolvedValue([]);
    const job = { id: '1' } as Job;
    await processor.process(job);
    expect(prodRepo.find).toHaveBeenCalledWith({ where: { isActive: true } });
    expect(embRepo.findOne).not.toHaveBeenCalled();
  });

  it('should skip products that already have a valid embedding', async () => {
    prodRepo.find.mockResolvedValue([{ id: 'prod1', name: 'Product 1', isActive: true }]);
    embRepo.findOne.mockResolvedValue({ productId: 'prod1', embeddingClip: 'pending' });

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect(embRepo.findOne).toHaveBeenCalledWith({ where: { productId: 'prod1' } });
    expect(embRepo.save).not.toHaveBeenCalled();
  });

  it('should process a product without an image url', async () => {
    prodRepo.find.mockResolvedValue([{ id: 'prod1', name: 'Product 1', description: 'Desc 1', isActive: true }]);
    embRepo.findOne.mockResolvedValue(null);

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect(embRepo.save).toHaveBeenCalled();
    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.productId).toBe('prod1');
    expect(savedArg.content).toBe('Product 1: Desc 1');
    expect(savedArg.embedding).toBe('[0.1,0.2,0.3]');
    expect(savedArg.embeddingClip).toBeNull();
  });

  it('should handle product with image url correctly', async () => {
    prodRepo.find.mockResolvedValue([{
      id: 'prod1',
      name: 'Product 1',
      imageUrl: 'http://example.com/products/img1.jpg',
      isActive: true
    }]);
    embRepo.findOne.mockResolvedValue(null);

    const mockTransformToByteArray = jest.fn();
    (processor as any).s3.send.mockResolvedValue({
      Body: {
        transformToByteArray: mockTransformToByteArray
      }
    });

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect((processor as any).s3.send).toHaveBeenCalled();
    expect(mockTransformToByteArray).toHaveBeenCalled();
    expect(embRepo.save).toHaveBeenCalled();

    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.embeddingClip).toBe('pending');
  });

  it('should handle missing body from S3 response gracefully', async () => {
    prodRepo.find.mockResolvedValue([{
      id: 'prod1',
      name: 'Product 1',
      imageUrl: 'http://example.com/products/img1.jpg',
      isActive: true
    }]);
    embRepo.findOne.mockResolvedValue(null);

    (processor as any).s3.send.mockResolvedValue({
      Body: null // Mocking a missing body
    });

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect((processor as any).s3.send).toHaveBeenCalled();
    expect(embRepo.save).toHaveBeenCalled();

    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.embeddingClip).toBe('pending'); // The code sets this regardless of body processing if key exists
  });

  it('should handle missing key from imageUrl gracefully', async () => {
    prodRepo.find.mockResolvedValue([{
      id: 'prod1',
      name: 'Product 1',
      imageUrl: 'invalid-url-format', // Missing /products/ to split
      isActive: true
    }]);
    embRepo.findOne.mockResolvedValue(null);

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect((processor as any).s3.send).not.toHaveBeenCalled();
    expect(embRepo.save).toHaveBeenCalled();

    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.embeddingClip).toBeNull();
  });

  it('should catch text embedding errors and save product without text embedding', async () => {
    prodRepo.find.mockResolvedValue([{ id: 'prod1', name: 'Product 1', isActive: true }]);
    embRepo.findOne.mockResolvedValue(null);

    // Override OpenAI mock just for this test
    (OpenAI as unknown as jest.Mock).mockImplementationOnce(() => ({
      embeddings: {
        create: jest.fn().mockRejectedValue(new Error('OpenAI error'))
      }
    }));

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect(embRepo.save).toHaveBeenCalled();
    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.embedding).toBeNull();
  });

  it('should catch image processing errors but continue to save product', async () => {
    prodRepo.find.mockResolvedValue([{
      id: 'prod1',
      name: 'Product 1',
      imageUrl: 'http://example.com/products/img1.jpg',
      isActive: true
    }]);
    embRepo.findOne.mockResolvedValue(null);

    (processor as any).s3.send.mockRejectedValue(new Error('S3 error'));

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect(embRepo.save).toHaveBeenCalled();
    const savedArg = embRepo.save.mock.calls[0][0];
    expect(savedArg.embeddingClip).toBeNull();
    // But text embedding should still work
    expect(savedArg.embedding).toBe('[0.1,0.2,0.3]');
  });

  it('should handle repository save errors', async () => {
    prodRepo.find.mockResolvedValue([{ id: 'prod1', name: 'Product 1', isActive: true }]);
    embRepo.findOne.mockResolvedValue(null);
    embRepo.save.mockRejectedValue(new Error('DB error'));

    const job = { id: '1' } as Job;
    await processor.process(job);

    expect(embRepo.save).toHaveBeenCalled();
    // Should not crash, just logs the error and finishes
  });
});
