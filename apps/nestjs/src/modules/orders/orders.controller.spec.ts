import { Test, TestingModule } from '@nestjs/testing';
import { OrdersController } from './orders.controller';
import { Order } from '../../entities';
import { getRepositoryToken } from '@nestjs/typeorm';

describe('OrdersController', () => {
  let controller: OrdersController;

  const mockQueryBuilder = {
    orderBy: jest.fn().mockReturnThis(),
    skip: jest.fn().mockReturnThis(),
    take: jest.fn().mockReturnThis(),
    andWhere: jest.fn().mockReturnThis(),
    getManyAndCount: jest.fn().mockResolvedValue([[], 0]),
  };

  const mockRepository = {
    createQueryBuilder: jest.fn().mockReturnValue(mockQueryBuilder),
    findOne: jest.fn().mockResolvedValue(null),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [OrdersController],
      providers: [
        {
          provide: getRepositoryToken(Order),
          useValue: mockRepository,
        },
      ],
    }).compile();

    controller = module.get<OrdersController>(OrdersController);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('list', () => {
    it('should return a list of orders with pagination', async () => {
      const orders = [{ id: '1' }, { id: '2' }];
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([orders, 2]);

      const result = await controller.list(undefined, 1, 20);

      expect(mockRepository.createQueryBuilder).toHaveBeenCalledWith('o');
      expect(mockQueryBuilder.orderBy).toHaveBeenCalledWith('o.createdAt', 'DESC');
      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(0);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(20);
      expect(mockQueryBuilder.getManyAndCount).toHaveBeenCalled();

      expect(result).toEqual({ orders, total: 2, page: 1, limit: 20 });
    });

    it('should filter by status if provided', async () => {
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([[], 0]);

      await controller.list('pending', 1, 20);

      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('o.status = :status', { status: 'pending' });
    });

    it('should calculate skip correctly for different pages', async () => {
      mockQueryBuilder.getManyAndCount.mockResolvedValueOnce([[], 0]);

      await controller.list(undefined, 3, 10);

      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(20);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(10);
    });
  });

  describe('get', () => {
    it('should return a single order by id', async () => {
      const order = { id: '1', status: 'completed' };
      mockRepository.findOne.mockResolvedValueOnce(order);

      const result = await controller.get('1');

      expect(mockRepository.findOne).toHaveBeenCalledWith({ where: { id: '1' } });
      expect(result).toEqual(order);
    });

    it('should return null if order is not found', async () => {
      mockRepository.findOne.mockResolvedValueOnce(null);

      const result = await controller.get('999');

      expect(mockRepository.findOne).toHaveBeenCalledWith({ where: { id: '999' } });
      expect(result).toBeNull();
    });
  });
});
