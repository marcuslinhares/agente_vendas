import { DataSource } from 'typeorm';
import { entities } from './entities';

export default new DataSource({
  type: 'postgres',
  url: process.env.DATABASE_URL || 'postgresql://app:localdev@localhost:5432/agentevendas',
  entities,
  migrations: ['src/migrations/*.ts'],
  synchronize: false,
});
