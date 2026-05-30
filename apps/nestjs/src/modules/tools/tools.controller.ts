import { Controller, Get, Post, Put, Param, Body, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ToolCatalog } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { IsString, IsOptional, IsBoolean, IsObject } from 'class-validator';
import Redis from 'ioredis';

class CreateToolDto {
  @IsString()
  name!: string;

  @IsString()
  description!: string;

  @IsObject()
  schema!: Record<string, any>;

  @IsString()
  endpoint!: string;

  @IsOptional()
  @IsString()
  httpMethod?: string;

  @IsOptional()
  @IsObject()
  headers?: Record<string, string>;

  @IsOptional()
  @IsString()
  category?: string;

  @IsOptional()
  rateLimit?: number;

  @IsOptional()
  timeoutMs?: number;

  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}

@Controller('tools')
@UseGuards(JwtAuthGuard)
export class ToolsController {
  private redis: Redis;

  constructor(
    @InjectRepository(ToolCatalog)
    private readonly repo: Repository<ToolCatalog>,
  ) {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  @Get()
  async list(): Promise<ToolCatalog[]> {
    return this.repo.find({ where: { isActive: true }, order: { name: 'ASC' } });
  }

  @Get('all')
  async listAll(): Promise<ToolCatalog[]> {
    return this.repo.find({ order: { name: 'ASC' } });
  }

  @Get(':id')
  async get(@Param('id') id: string): Promise<ToolCatalog | null> {
    return this.repo.findOne({ where: { id } });
  }

  @Post()
  async create(@Body() dto: CreateToolDto): Promise<ToolCatalog> {
    const tool = this.repo.create({
      name: dto.name,
      description: dto.description,
      schema: dto.schema,
      endpoint: dto.endpoint,
      httpMethod: dto.httpMethod || 'POST',
      headers: dto.headers || {},
      category: dto.category,
      rateLimit: dto.rateLimit || 0,
      timeoutMs: dto.timeoutMs || 10000,
      isActive: dto.isActive ?? true,
    });
    const saved = await this.repo.save(tool);
    await this.invalidateCache();
    return saved;
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() dto: Partial<CreateToolDto>): Promise<ToolCatalog | null> {
    await this.repo.update(id, dto as any);
    await this.invalidateCache();
    return this.repo.findOne({ where: { id } });
  }

  @Post(':id/test')
  async test(@Param('id') id: string): Promise<{ ok: boolean; status?: number; body?: string; error?: string }> {
    const tool = await this.repo.findOne({ where: { id } });
    if (!tool) return { ok: false, error: 'Tool not found' };

    try {
      const response = await fetch(tool.endpoint, {
        method: tool.httpMethod || 'POST',
        headers: { 'Content-Type': 'application/json', ...(tool.headers || {}) } as any,
        body: JSON.stringify({ test: true }),
      });
      return { ok: true, status: response.status, body: await response.text().catch(() => '') };
    } catch (e: any) {
      return { ok: false, error: e.message };
    }
  }

  private async invalidateCache(): Promise<void> {
    await this.redis.publish('tools:updated', JSON.stringify({ action: 'updated' }));
  }
}
