import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('product_embeddings')
export class ProductEmbedding {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'product_id' })
  productId!: string;

  @Column({ type: 'text', nullable: true })
  content!: string;

  @Column({ name: 'media_url', type: 'text', nullable: true })
  mediaUrl!: string;

  /** Stores VECTOR(1536) as a JSON-serialized array */
  @Column({ type: 'text', nullable: true })
  embedding!: string;

  /** Stores VECTOR(512) as a JSON-serialized array */
  @Column({ name: 'embedding_clip', type: 'text', nullable: true })
  embeddingClip!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
