'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  MessageSquare,
  Users,
  Wrench,
  TrendingUp,
} from 'lucide-react';

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => apiClient<any>('/analytics/overview'),
  });

  if (isLoading) return <div className="p-8">Carregando...</div>;

  if (!data) return <div className="p-8">Sem dados disponíveis</div>;

  const stats = [
    { title: 'Conversas', value: data.conversations?.total || 0, icon: MessageSquare, color: 'blue' },
    { title: 'Ativas', value: data.conversations?.active || 0, icon: TrendingUp, color: 'green' },
    { title: 'Mensagens', value: data.messages || 0, icon: Users, color: 'orange' },
    { title: 'Tools Executadas', value: data.toolCalls || 0, icon: Wrench, color: 'purple' },
  ];

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
  };

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold">Analytics</h2>

      <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <div className="flex items-center gap-4">
                <div className={`rounded-lg p-3 ${colorMap[stat.color]}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">{stat.title}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Classificação de Leads</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {data.byClassification?.map((item: any) => (
              <div key={item.classification} className="flex items-center justify-between">
                <span className="text-sm capitalize">{item.classification?.replace('_', ' ')}</span>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-32 rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{
                        width: `${(item.count / (data.conversations?.total || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm font-medium">{item.count}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Tools</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {data.topTools?.map((item: any, i: number) => (
              <div key={item.tool} className="flex items-center justify-between">
                <span className="text-sm">
                  <span className="mr-2 font-mono text-gray-400">#{i + 1}</span>
                  {item.tool}
                </span>
                <Badge>{item.count} chamadas</Badge>
              </div>
            ))}
            {(!data.topTools || data.topTools.length === 0) && (
              <p className="text-sm text-gray-500">Nenhuma tool executada ainda</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
