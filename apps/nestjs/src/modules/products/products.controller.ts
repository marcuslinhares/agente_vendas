import { Controller, Get, Post, Put, Delete, Param, Body, Query, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Product } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { IsString, IsNumber, IsOptional, Min, IsBoolean } from 'class-validator';
import { Type } from 'class-transformer';

class CreateProductDto {
  @IsString()
  name!: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsNumber()
  @Min(0)
  @Type(() => Number)
  price!: number;

  @IsOptional()
  @IsString()
  category?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @Type(() => Number)
  stock?: number;
}

class UpdateProductDto {
  @IsOptional()
  @IsString()
  name?: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @Type(() => Number)
  price?: number;

  @IsOptional()
  @IsString()
  category?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  @Type(() => Number)
  stock?: number;

  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}

@Controller('products')
@UseGuards(JwtAuthGuard)
export class ProductsController {
  constructor(
    @InjectRepository(Product)
    private readonly repo: Repository<Product>,
  ) {}

  @Get()
  async list(
    @Query('category') category?: string,
    @Query('search') search?: string,
    @Query('page') page = 1,
    @Query('limit') limit = 10,
  ) {
    const qb = this.repo.createQueryBuilder('p')
      .where('p.isActive = true')
      .orderBy('p.name', 'ASC')
      .skip((page - 1) * limit)
      .take(limit);

    if (category) qb.andWhere('p.category = :category', { category });
    if (search) qb.andWhere('p.name ILIKE :search', { search: `%${search}%` });

    const [products, total] = await qb.getManyAndCount();
    return { products, total, page, limit };
  }

  @Get(':id')
  async get(@Param('id') id: string) {
    return this.repo.findOne({ where: { id } });
  }

  @Post()
  async create(@Body() dto: CreateProductDto) {
    const product = this.repo.create(dto);
    return this.repo.save(product);
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() dto: UpdateProductDto) {
    await this.repo.update(id, dto);
    return this.repo.findOne({ where: { id } });
  }

  @Delete(':id')
  async remove(@Param('id') id: string) {
    await this.repo.update(id, { isActive: false });
    return { ok: true };
  }
}
