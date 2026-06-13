import { Test, TestingModule } from '@nestjs/testing';
import { ProductsController } from './products.controller';
import { getRepositoryToken } from '@nestjs/typeorm';
import { Product } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { ExecutionContext } from '@nestjs/common';

describe('ProductsController', () => {
  let controller: ProductsController;

  const mockProduct = {
    id: '1',
    name: 'Test Product',
    description: 'Test Description',
    price: 100,
    category: 'Test Category',
    stock: 10,
    isActive: true,
  };

  const mockQueryBuilder = {
    where: jest.fn().mockReturnThis(),
    orderBy: jest.fn().mockReturnThis(),
    skip: jest.fn().mockReturnThis(),
    take: jest.fn().mockReturnThis(),
    andWhere: jest.fn().mockReturnThis(),
    getManyAndCount: jest.fn().mockResolvedValue([[mockProduct], 1]),
  };

  const mockRepository = {
    createQueryBuilder: jest.fn(() => mockQueryBuilder),
    findOne: jest.fn().mockResolvedValue(mockProduct),
    create: jest.fn().mockImplementation((dto) => dto),
    save: jest.fn().mockImplementation((product) => Promise.resolve({ id: '1', ...product })),
    update: jest.fn().mockResolvedValue({ affected: 1 }),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ProductsController],
      providers: [
        {
          provide: getRepositoryToken(Product),
          useValue: mockRepository,
        },
      ],
    })
      .overrideGuard(JwtAuthGuard)
      .useValue({
        canActivate: (context: ExecutionContext) => true,
      })
      .compile();

    controller = module.get<ProductsController>(ProductsController);
    jest.clearAllMocks();
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('list', () => {
    it('should return a list of products', async () => {
      const result = await controller.list(undefined, undefined, 1, 10);
      expect(result).toEqual({ products: [mockProduct], total: 1, page: 1, limit: 10 });
      expect(mockRepository.createQueryBuilder).toHaveBeenCalledWith('p');
      expect(mockQueryBuilder.where).toHaveBeenCalledWith('p.isActive = true');
      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(0);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(10);
    });

    it('should handle category and search queries', async () => {
      const result = await controller.list('test-category', 'test-search', 2, 5);
      expect(result).toEqual({ products: [mockProduct], total: 1, page: 2, limit: 5 });
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('p.category = :category', { category: 'test-category' });
      expect(mockQueryBuilder.andWhere).toHaveBeenCalledWith('p.name ILIKE :search', { search: '%test-search%' });
      expect(mockQueryBuilder.skip).toHaveBeenCalledWith(5);
      expect(mockQueryBuilder.take).toHaveBeenCalledWith(5);
    });
  });

  describe('get', () => {
    it('should return a product by id', async () => {
      const result = await controller.get('1');
      expect(result).toEqual(mockProduct);
      expect(mockRepository.findOne).toHaveBeenCalledWith({ where: { id: '1' } });
    });
  });

  describe('create', () => {
    it('should create and return a new product', async () => {
      const dto = { name: 'New Product', price: 50 };
      const result = await controller.create(dto);
      expect(result).toEqual({ id: '1', ...dto });
      expect(mockRepository.create).toHaveBeenCalledWith(dto);
      expect(mockRepository.save).toHaveBeenCalledWith(dto);
    });
  });

  describe('update', () => {
    it('should update a product and return it', async () => {
      const dto = { name: 'Updated Product' };
      const result = await controller.update('1', dto);
      expect(result).toEqual(mockProduct);
      expect(mockRepository.update).toHaveBeenCalledWith('1', dto);
      expect(mockRepository.findOne).toHaveBeenCalledWith({ where: { id: '1' } });
    });
  });

  describe('remove', () => {
    it('should soft delete a product by setting isActive to false', async () => {
      const result = await controller.remove('1');
      expect(result).toEqual({ ok: true });
      expect(mockRepository.update).toHaveBeenCalledWith('1', { isActive: false });
    });
  });
});
