import { Test, TestingModule } from '@nestjs/testing';
import { ProductsController } from './products.controller';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Product } from '../../entities';
import { Repository } from 'typeorm';

describe('ProductsController', () => {
  let controller: ProductsController;
  let repo: Repository<Product>;

  const mockQueryBuilder = {
    where: jest.fn().mockReturnThis(),
    orderBy: jest.fn().mockReturnThis(),
    skip: jest.fn().mockReturnThis(),
    take: jest.fn().mockReturnThis(),
    andWhere: jest.fn().mockReturnThis(),
    getManyAndCount: jest.fn().mockResolvedValue([[{ id: '1', name: 'Test Product' }], 1]),
  };

  const mockRepo = {
    createQueryBuilder: jest.fn().mockReturnValue(mockQueryBuilder),
    findOne: jest.fn(),
    create: jest.fn(),
    save: jest.fn(),
    update: jest.fn(),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ProductsController],
      providers: [
        {
          provide: getRepositoryToken(Product),
          useValue: mockRepo,
        },
      ],
    }).compile();

    controller = module.get<ProductsController>(ProductsController);
    repo = module.get<Repository<Product>>(getRepositoryToken(Product));
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('list', () => {
    it('should list products with default pagination', async () => {
      const result = await controller.list();
      expect(repo.createQueryBuilder).toHaveBeenCalledWith('p');
      expect(mockQueryBuilder.where).toHaveBeenCalledWith('p.isActive = true');
      expect(mockQueryBuilder.orderBy).toHaveBeenCalledWith('p.name', 'ASC');
      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(0);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(10);
      expect(mockQueryBuilder.getManyAndCount).toHaveBeenCalled();

      expect(result).toEqual({
        products: [{ id: '1', name: 'Test Product' }],
        total: 1,
        page: 1,
        limit: 10,
      });
    });

    it('should apply category filter', async () => {
      await controller.list('electronics');
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('p.category = :category', { category: 'electronics' });
    });

    it('should apply search filter', async () => {
      await controller.list(undefined, 'phone');
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('p.name ILIKE :search', { search: '%phone%' });
    });

    it('should apply pagination parameters', async () => {
      await controller.list(undefined, undefined, 2, 20);
      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(20);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(20);
    });
  });

  describe('get', () => {
    it('should return a product by id', async () => {
      const mockProduct = { id: '1', name: 'Test Product' };
      mockRepo.findOne.mockResolvedValueOnce(mockProduct);

      const result = await controller.get('1');
      expect(repo.findOne).toHaveBeenCalledWith({ where: { id: '1' } });
      expect(result).toEqual(mockProduct);
    });
  });

  describe('create', () => {
    it('should create and save a new product', async () => {
      const createDto = { name: 'New Product', price: 100 };
      const mockProduct = { id: '1', ...createDto };
      mockRepo.create.mockReturnValueOnce(mockProduct);
      mockRepo.save.mockResolvedValueOnce(mockProduct);

      const result = await controller.create(createDto as any);
      expect(repo.create).toHaveBeenCalledWith(createDto);
      expect(repo.save).toHaveBeenCalledWith(mockProduct);
      expect(result).toEqual(mockProduct);
    });
  });

  describe('update', () => {
    it('should update and return the product', async () => {
      const updateDto = { name: 'Updated Product' };
      const mockProduct = { id: '1', name: 'Updated Product' };
      mockRepo.findOne.mockResolvedValueOnce(mockProduct);

      const result = await controller.update('1', updateDto as any);
      expect(repo.update).toHaveBeenCalledWith('1', updateDto);
      expect(repo.findOne).toHaveBeenCalledWith({ where: { id: '1' } });
      expect(result).toEqual(mockProduct);
    });
  });

  describe('remove', () => {
    it('should soft delete the product', async () => {
      const result = await controller.remove('1');
      expect(repo.update).toHaveBeenCalledWith('1', { isActive: false });
      expect(result).toEqual({ ok: true });
    });
  });
});
