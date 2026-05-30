import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('messages')
export class Message {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'message_id', type: 'text', unique: true })
  messageId!: string;

  @Column({ name: 'conversation_id' })
  conversationId!: string;

  @Column({ type: 'varchar', length: 10 })
  role!: string;

  @Column({ type: 'text', nullable: true })
  content!: string;

  @Column({ name: 'media_url', type: 'text', nullable: true })
  mediaUrl!: string;

  @Column({ name: 'thumbnail_url', type: 'text', nullable: true })
  thumbnailUrl!: string;

  @Column({ name: 'media_type', type: 'varchar', length: 20, nullable: true })
  mediaType!: string;

  @Column({ type: 'jsonb', default: {} })
  metadata!: Record<string, unknown>;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
