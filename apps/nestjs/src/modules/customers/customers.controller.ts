import { Controller, Get, Post, Param, Body, Query, UseGuards } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Customer } from '../../entities';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { IsString, IsOptional, IsIn } from 'class-validator';

class ClassifyDto {
  @IsString()
  conversationId!: string;

  @IsString()
  @IsIn(['lead_quente', 'lead_morno', 'lead_frio', 'cliente'])
  classification!: string;
}

@Controller('customers')
@UseGuards(JwtAuthGuard)
export class CustomersController {
  constructor(
    @InjectRepository(Customer)
    private readonly repo: Repository<Customer>,
  ) {}

  @Get()
  async list(
    @Query('classification') classification?: string,
    @Query('search') search?: string,
  ) {
    const qb = this.repo.createQueryBuilder('c').orderBy('c.lastContactAt', 'DESC');
    if (classification) qb.andWhere('c.classification = :classification', { classification });
    if (search) qb.andWhere('c.name ILIKE :search OR c.whatsappId ILIKE :search', { search: `%${search}%` });
    return qb.getMany();
  }

  @Get(':id')
  async get(@Param('id') id: string) {
    return this.repo.findOne({ where: { id } });
  }

  @Post('classify')
  async classify(@Body() dto: ClassifyDto) {
    await this.repo.createQueryBuilder()
      .update(Customer)
      .set({ classification: dto.classification })
      .where('"whatsapp_id" IN (SELECT "whatsapp_id" FROM conversations WHERE id = :convId)', { convId: dto.conversationId })
      .execute();
    return { ok: true, classification: dto.classification };
  }
}
