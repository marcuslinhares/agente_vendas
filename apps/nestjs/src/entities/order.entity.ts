import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('orders')
export class Order {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'customer_id' })
  customerId!: string;

  @Column({ name: 'conversation_id', nullable: true })
  conversationId!: string;

  @Column({ type: 'jsonb', default: [] })
  items!: Record<string, unknown>[];

  @Column({ type: 'decimal', precision: 10, scale: 2 })
  total!: number;

  @Column({ default: 'pending' })
  status!: string;

  @Column({ name: 'payment_method', type: 'varchar', length: 50, nullable: true })
  paymentMethod!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
