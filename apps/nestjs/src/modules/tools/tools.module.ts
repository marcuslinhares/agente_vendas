import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ToolsController } from './tools.controller';
import { ToolCatalog } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([ToolCatalog])],
  controllers: [ToolsController],
})
export class ToolsModule {}
