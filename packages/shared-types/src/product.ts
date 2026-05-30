import { z } from "zod";

export const ProductSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().optional(),
  price: z.number().positive(),
  category: z.string().optional(),
  stock: z.number().int().nonnegative().default(0),
  image_url: z.string().optional(),
  is_active: z.boolean().default(true),
});

export type Product = z.infer<typeof ProductSchema>;
