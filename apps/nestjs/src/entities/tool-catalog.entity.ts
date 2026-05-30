import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity('tools_catalog')
export class ToolCatalog {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 100, unique: true })
  name!: string;

  @Column({ type: 'text' })
  description!: string;

  @Column({ type: 'jsonb', default: {} })
  schema!: Record<string, unknown>;

  @Column({ type: 'text' })
  endpoint!: string;

  @Column({ name: 'http_method', type: 'varchar', length: 10, default: 'POST' })
  httpMethod!: string;

  @Column({ type: 'jsonb', default: {} })
  headers!: Record<string, unknown>;

  @Column({ type: 'varchar', length: 50, nullable: true })
  category!: string;

  @Column({ name: 'rate_limit', type: 'int', default: 0 })
  rateLimit!: number;

  @Column({ name: 'timeout_ms', type: 'int', default: 10000 })
  timeoutMs!: number;

  @Column({ name: 'is_active', default: true })
  isActive!: boolean;

  @Column({ name: 'is_idempotent', default: true })
  isIdempotent!: boolean;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;
}
