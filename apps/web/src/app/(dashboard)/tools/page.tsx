'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Plus, Play } from 'lucide-react';

export default function ToolsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', endpoint: '', category: '' });

  const { data: tools, isLoading } = useQuery({
    queryKey: ['tools'],
    queryFn: () => apiClient<any[]>('/tools'),
  });

  const createMutation = useMutation({
    mutationFn: (body: any) => apiClient('/tools', {
      method: 'POST',
      body: JSON.stringify({ ...body, schema: {} }),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      setDialogOpen(false);
      setForm({ name: '', description: '', endpoint: '', category: '' });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => apiClient(`/tools/${id}/test`, { method: 'POST' }),
  });

  if (isLoading) return <div className="p-8">Carregando...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Tools</h2>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> Nova Tool
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {tools?.map((tool: any) => (
          <Card key={tool.id}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{tool.name}</h3>
                <p className="mt-1 text-sm text-gray-500">{tool.description}</p>
                <div className="mt-2 flex gap-2">
                  <Badge>{tool.httpMethod || 'POST'}</Badge>
                  {tool.category && <Badge variant="warning">{tool.category}</Badge>}
                </div>
                <p className="mt-2 text-xs text-gray-400">{tool.endpoint}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => testMutation.mutate(tool.id)}
                disabled={testMutation.isPending}
              >
                <Play className="mr-1 h-3 w-3" /> Testar
              </Button>
            </div>
            {testMutation.data && testMutation.variables === tool.id && (
              <div className="mt-3 rounded bg-gray-50 p-2 text-xs">
                Status: {testMutation.data.status} — {testMutation.data.body?.slice(0, 200)}
              </div>
            )}
          </Card>
        ))}
      </div>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Nova Tool">
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Nome</label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Descrição</label>
            <Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Endpoint</label>
            <Input value={form.endpoint} onChange={e => setForm({ ...form, endpoint: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Categoria</label>
            <Input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button type="submit" disabled={createMutation.isPending}>Criar</Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
