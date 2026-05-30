import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('message_embeddings')
export class MessageEmbedding {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'conversation_id' })
  conversationId!: string;

  @Column({ name: 'message_id', nullable: true })
  messageId!: string;

  @Column({ type: 'text', nullable: true })
  content!: string;

  @Column({ name: 'media_url', type: 'text', nullable: true })
  mediaUrl!: string;

  @Column({ name: 'media_type', type: 'varchar', length: 20, nullable: true })
  mediaType!: string;

  /** Stores VECTOR(1536) as a JSON-serialized array */
  @Column({ type: 'text', nullable: true })
  embedding!: string;

  /** Stores VECTOR(512) as a JSON-serialized array */
  @Column({ name: 'embedding_clip', type: 'text', nullable: true })
  embeddingClip!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
