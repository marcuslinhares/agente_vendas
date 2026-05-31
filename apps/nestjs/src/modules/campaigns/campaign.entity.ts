import { Entity, Column, PrimaryGeneratedColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('campaigns')
export class Campaign {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column()
  name!: string;

  @Column({ type: 'text', nullable: true })
  messageTemplate!: string;

  @Column({ nullable: true })
  targetClassification!: string;

  @Column({ nullable: true })
  scheduledAt!: Date;

  @Column({ default: 'draft' })
  status!: string;

  @Column({ default: 0 })
  sentCount!: number;

  @Column({ default: 0 })
  totalTarget!: number;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;
}
