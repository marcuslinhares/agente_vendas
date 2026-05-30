import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('tool_execution_log')
export class ToolExecutionLog {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'tool_name', type: 'varchar', length: 100 })
  toolName!: string;

  @Column({ name: 'conversation_id', nullable: true })
  conversationId!: string;

  @Column({ type: 'jsonb', default: {} })
  parameters!: Record<string, unknown>;

  @Column({ type: 'text', nullable: true })
  response!: string;

  @Column({ name: 'duration_ms', type: 'int', nullable: true })
  durationMs!: number;

  @Column({ default: false })
  success!: boolean;

  @Column({ name: 'error_message', type: 'text', nullable: true })
  errorMessage!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
