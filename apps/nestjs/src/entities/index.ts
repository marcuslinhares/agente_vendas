import { Conversation } from './conversation.entity';
import { Message } from './message.entity';
import { MessageEmbedding } from './message-embedding.entity';
import { Product } from './product.entity';
import { ProductEmbedding } from './product-embedding.entity';
import { Customer } from './customer.entity';
import { Order } from './order.entity';
import { ToolCatalog } from './tool-catalog.entity';
import { ToolExecutionLog } from './tool-execution-log.entity';
import { User } from './user.entity';

export { Conversation, Message, MessageEmbedding, Product, ProductEmbedding, Customer, Order, ToolCatalog, ToolExecutionLog, User };

export const entities = [
  Conversation,
  Message,
  MessageEmbedding,
  Product,
  ProductEmbedding,
  Customer,
  Order,
  ToolCatalog,
  ToolExecutionLog,
  User,
];
