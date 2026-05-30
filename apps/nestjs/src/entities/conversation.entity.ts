import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity('conversations')
export class Conversation {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'whatsapp_id', type: 'text', unique: true })
  whatsappId!: string;

  @Column({ name: 'customer_id', nullable: true })
  customerId!: string;

  @Column({ default: 'active' })
  status!: string;

  @Column({ type: 'text', nullable: true })
  summary!: string;

  @Column({ name: 'summary_version', default: 0 })
  summaryVersion!: number;

  @Column({ name: 'message_count', default: 0 })
  messageCount!: number;

  @Column({ nullable: true })
  classification!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;
}
