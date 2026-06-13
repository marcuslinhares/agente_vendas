import { Test, TestingModule } from '@nestjs/testing';
import { getRepositoryToken } from '@nestjs/typeorm';
import { PersistConsumer } from './persist.consumer';
import { Message, Conversation, MessageEmbedding, Customer } from '../entities';
import Redis from 'ioredis';

jest.mock('ioredis');

describe('PersistConsumer', () => {
  let consumer: PersistConsumer;
  let mockRedis: jest.Mocked<Redis>;

  const mockMsgRepo = {
    findOne: jest.fn(),
    create: jest.fn(),
    save: jest.fn(),
  };

  const mockConvRepo = {
    increment: jest.fn(),
  };

  const mockEmbRepo = {
    create: jest.fn(),
    save: jest.fn(),
  };

  const mockCustRepo = {
    update: jest.fn(),
  };

  beforeEach(async () => {
    jest.clearAllMocks();

    (Redis as unknown as jest.Mock).mockImplementation(() => {
      return {
        xgroup: jest.fn(),
        xreadgroup: jest.fn(),
        xack: jest.fn(),
      };
    });

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        PersistConsumer,
        {
          provide: getRepositoryToken(Message),
          useValue: mockMsgRepo,
        },
        {
          provide: getRepositoryToken(Conversation),
          useValue: mockConvRepo,
        },
        {
          provide: getRepositoryToken(MessageEmbedding),
          useValue: mockEmbRepo,
        },
        {
          provide: getRepositoryToken(Customer),
          useValue: mockCustRepo,
        },
      ],
    }).compile();

    consumer = module.get<PersistConsumer>(PersistConsumer);
    mockRedis = (consumer as any).redis;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('ensureGroup', () => {
    it('should ignore BUSYGROUP error', async () => {
      mockRedis.xgroup = jest.fn().mockRejectedValue(new Error('BUSYGROUP Consumer Group name already exists'));

      await expect((consumer as any).ensureGroup()).resolves.toBeUndefined();
      expect(mockRedis.xgroup).toHaveBeenCalled();
    });

    it('should re-throw other errors', async () => {
      const error = new Error('Some other error');
      mockRedis.xgroup = jest.fn().mockRejectedValue(error);

      await expect((consumer as any).ensureGroup()).rejects.toThrow(error);
    });
  });

  describe('startConsumer', () => {
    it('should handle xreadgroup error and log it, then sleep 5s', async () => {
      const loggerErrorSpy = jest.spyOn((consumer as any).logger, 'error').mockImplementation(() => {});

      const expectedError = new Error('Redis connection failed');

      mockRedis.xreadgroup = jest.fn().mockRejectedValue(expectedError);

      const setTimeoutSpy = jest.spyOn(global, 'setTimeout').mockImplementation((cb: any, ms: any) => {
         // Throw an error to escape the infinite loop immediately when setTimeout is called
         throw new Error('ESCAPE_LOOP');
      });

      try {
          await (consumer as any).startConsumer();
      } catch (e: any) {
          if (e.message !== 'ESCAPE_LOOP') throw e;
      }

      expect(loggerErrorSpy).toHaveBeenCalledWith(`Error in persist stream loop: ${expectedError.message}`);
      expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 5000);

      setTimeoutSpy.mockRestore();
    });
  });
});
