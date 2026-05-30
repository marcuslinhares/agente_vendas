'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'danger'> = {
  pending: 'warning',
  confirmed: 'success',
  shipped: 'default',
  cancelled: 'danger',
};

export default function OrdersPage() {
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => apiClient<any>('/orders'),
  });

  const orders = data?.orders || [];

  const filtered = statusFilter
    ? orders.filter((o: any) => o.status === statusFilter)
    : orders;

  if (isLoading) return <div className="p-8">Carregando...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Pedidos</h2>
        <div className="flex gap-2">
          {['', 'pending', 'confirmed', 'shipped', 'cancelled'].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1 text-sm ${
                statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s || 'Todos'}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">ID</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Total</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Pagamento</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Data</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((order: any) => (
              <tr key={order.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-sm">{order.id?.slice(0, 8)}</td>
                <td className="px-4 py-3 font-medium">
                  R$ {parseFloat(order.total || 0).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <Badge variant={statusColors[order.status] || 'default'}>{order.status}</Badge>
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">{order.paymentMethod || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {new Date(order.createdAt).toLocaleDateString('pt-BR')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="py-8 text-center text-gray-500">Nenhum pedido encontrado</p>
        )}
      </div>
    </div>
  );
}
