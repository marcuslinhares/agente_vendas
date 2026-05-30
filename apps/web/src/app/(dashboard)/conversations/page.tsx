'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Search } from 'lucide-react';

const statusColor: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  active: 'success',
  closed: 'default',
  followup: 'warning',
};

const classColor: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  lead_quente: 'success',
  lead_morno: 'warning',
  lead_frio: 'danger',
  cliente: 'default',
};

export default function ConversationsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');

  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => apiClient<any[]>('/conversations'),
  });

  const filtered = conversations?.filter((c: any) =>
    c.whatsappId?.toLowerCase().includes(search.toLowerCase()),
  );

  if (isLoading) return <div className="p-8">Carregando...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Conversas</h2>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Buscar por número..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <div className="space-y-3">
        {filtered?.map((conv: any) => (
          <div
            key={conv.id}
            onClick={() => router.push(`/conversations/${conv.id}`)}
            className="flex cursor-pointer items-center justify-between rounded-lg border bg-white p-4 transition-colors hover:bg-gray-50"
          >
            <div className="flex items-center gap-4">
              <div className="rounded-full bg-blue-100 p-3">
                <MessageSquare className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="font-medium">{conv.whatsappId}</p>
                <p className="text-sm text-gray-500">
                  {conv.messageCount || 0} mensagens
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {conv.classification && (
                <Badge variant={classColor[conv.classification] || 'default'}>
                  {conv.classification.replace('lead_', '')}
                </Badge>
              )}
              <Badge variant={statusColor[conv.status] || 'default'}>
                {conv.status}
              </Badge>
            </div>
          </div>
        ))}
        {filtered?.length === 0 && (
          <p className="py-8 text-center text-gray-500">Nenhuma conversa encontrada</p>
        )}
      </div>
    </div>
  );
}
