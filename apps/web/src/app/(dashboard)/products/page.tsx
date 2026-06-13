'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog } from '@/components/ui/dialog';
import { Plus, Edit2, Search } from 'lucide-react';

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<any>(null);
  const [form, setForm] = useState({ name: '', description: '', price: 0, category: '', stock: 0 });

  const { data, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => apiClient<any>('/products'),
  });

  const products = data?.products || data || [];

  const createMutation = useMutation({
    mutationFn: (body: any) => apiClient('/products', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setDialogOpen(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (body: any) => apiClient(`/products/${editingProduct.id}`, { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setDialogOpen(false);
      setEditingProduct(null);
      resetForm();
    },
  });

  function resetForm() {
    setForm({ name: '', description: '', price: 0, category: '', stock: 0 });
  }

  function openCreate() {
    setEditingProduct(null);
    resetForm();
    setDialogOpen(true);
  }

  function openEdit(product: any) {
    setEditingProduct(product);
    setForm({
      name: product.name,
      description: product.description || '',
      price: parseFloat(product.price) || 0,
      category: product.category || '',
      stock: product.stock || 0,
    });
    setDialogOpen(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editingProduct) {
      updateMutation.mutate(form);
    } else {
      createMutation.mutate(form);
    }
  }

  const filtered = products.filter((p: any) =>
    p.name?.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Produtos</h2>
        <div className="flex gap-3">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Buscar produtos..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" /> Novo Produto
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((product: any) => (
          <Card key={product.id}>
            <div className="flex h-full flex-col justify-between">
              <div>
                <div className="mb-2 flex items-start justify-between">
                  <h3 className="font-semibold">{product.name}</h3>
                  <button onClick={() => openEdit(product)} className="text-gray-400 hover:text-blue-600">
                    <Edit2 className="h-4 w-4" />
                  </button>
                </div>
                <p className="mb-2 text-sm text-gray-500">{product.description}</p>
                {product.category && <Badge>{product.category}</Badge>}
              </div>
              <div className="mt-4 flex items-center justify-between border-t pt-3">
                <span className="text-lg font-bold text-green-600">
                  R$ {parseFloat(product.price).toFixed(2)}
                </span>
                <span className={`text-sm ${product.stock > 0 ? 'text-gray-600' : 'text-red-500'}`}>
                  {product.stock > 0 ? `${product.stock} em estoque` : 'Fora de estoque'}
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}
        title={editingProduct ? 'Editar Produto' : 'Novo Produto'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Nome</label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Descrição</label>
            <Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Preço</label>
              <Input type="number" step="0.01" value={form.price}
                onChange={e => setForm({ ...form, price: parseFloat(e.target.value) || 0 })} required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Estoque</label>
              <Input type="number" value={form.stock}
                onChange={e => setForm({ ...form, stock: parseInt(e.target.value) || 0 })} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Categoria</label>
            <Input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingProduct ? 'Atualizar' : 'Criar'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
