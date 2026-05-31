import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { CampaignsController } from './campaigns.controller';
import { Campaign } from './campaign.entity';
import { Customer } from '../../entities';

@Module({
  imports: [TypeOrmModule.forFeature([Campaign, Customer])],
  controllers: [CampaignsController],
})
export class CampaignsModule {}
