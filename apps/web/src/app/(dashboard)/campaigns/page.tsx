'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog } from '@/components/ui/dialog';
import { Plus, Send, Calendar } from 'lucide-react';

export default function CampaignsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({
    name: '',
    messageTemplate: '',
    targetClassification: '',
  });

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => apiClient<any[]>('/campaigns'),
  });

  const createMutation = useMutation({
    mutationFn: (body: any) => apiClient('/campaigns', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      setDialogOpen(false);
      setForm({ name: '', messageTemplate: '', targetClassification: '' });
    },
  });

  const sendMutation = useMutation({
    mutationFn: (id: string) => apiClient(`/campaigns/${id}/send`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaigns'] }),
  });

  if (isLoading) return <div className="p-8">Carregando...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Campanhas</h2>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" /> Nova Campanha
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {campaigns?.map((camp: any) => (
          <Card key={camp.id}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{camp.name}</h3>
                <p className="mt-1 text-sm text-gray-500">{camp.messageTemplate?.slice(0, 100)}</p>
                <div className="mt-2 flex gap-2">
                  <Badge variant={camp.status === 'completed' ? 'success' : camp.status === 'scheduled' ? 'warning' : 'default'}>
                    {camp.status}
                  </Badge>
                  {camp.targetClassification && (
                    <Badge variant="warning">{camp.targetClassification}</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-400">
                  Enviadas: {camp.sentCount || 0} / {camp.totalTarget || 0}
                </p>
              </div>
              <div className="flex gap-2">
                {camp.status === 'draft' && (
                  <Button variant="outline" size="sm"
                    onClick={() => sendMutation.mutate(camp.id)}
                    disabled={sendMutation.isPending}>
                    <Send className="mr-1 h-3 w-3" /> Enviar
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Nova Campanha">
        <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Nome</label>
            <Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Mensagem</label>
            <textarea
              value={form.messageTemplate}
              onChange={e => setForm({ ...form, messageTemplate: e.target.value })}
              className="w-full rounded-md border p-2 text-sm"
              rows={4}
              placeholder="Olá {{nome}}, temos uma oferta especial..."
              required
            />
            <p className="mt-1 text-xs text-gray-400">Variáveis: {'{{nome}}'} {'{{whatsapp}}'}</p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Classificação alvo</label>
            <select
              value={form.targetClassification}
              onChange={e => setForm({ ...form, targetClassification: e.target.value })}
              className="w-full rounded-md border p-2 text-sm"
            >
              <option value="">Todos os clientes</option>
              <option value="lead_quente">Lead Quente</option>
              <option value="lead_morno">Lead Morno</option>
              <option value="lead_frio">Lead Frio</option>
              <option value="cliente">Cliente</option>
            </select>
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
