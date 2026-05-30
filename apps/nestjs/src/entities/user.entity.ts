import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
} from 'typeorm';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 255, unique: true })
  email!: string;

  @Column({ name: 'password_hash', type: 'varchar', length: 255 })
  passwordHash!: string;

  @Column({ type: 'varchar', length: 200, nullable: true })
  name!: string;

  @Column({ type: 'varchar', length: 20, default: 'admin' })
  role!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
