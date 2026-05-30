'use client';

import { useState } from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function SettingsPage() {
  const [config, setConfig] = useState({
    evolutionApiUrl: localStorage.getItem('EVOLUTION_API_URL') || '',
    openaiKey: localStorage.getItem('OPENAI_API_KEY')?.slice(0, 10) + '...' || '',
    webhookUrl: typeof window !== 'undefined' ? `${window.location.origin}/webhook/evolution` : '',
  });

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold">Configurações</h2>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Evolution API</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Webhook URL</label>
              <div className="flex items-center gap-2">
                <Input value={config.webhookUrl} readOnly className="bg-gray-50" />
                <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(config.webhookUrl)}>
                  Copiar
                </Button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Configure esta URL no painel da Evolution API para receber webhooks
              </p>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Status</label>
              <Badge variant="success">Conectado</Badge>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>OpenAI / LLM</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Modelo</label>
              <Input value="gpt-4o" readOnly className="bg-gray-50" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Chave API</label>
              <Input value={config.openaiKey} readOnly className="bg-gray-50" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Embedding Model</label>
              <Input value="text-embedding-3-small" readOnly className="bg-gray-50" />
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Serviços</CardTitle>
          </CardHeader>
          <div className="space-y-2">
            {[
              { name: 'Hono (Webhook)', status: 'online' },
              { name: 'FastAPI (LangGraph)', status: 'online' },
              { name: 'NestJS (API)', status: 'online' },
              { name: 'PostgreSQL + pgvector', status: 'online' },
              { name: 'Redis', status: 'online' },
              { name: 'MinIO', status: 'online' },
            ].map((svc) => (
              <div key={svc.name} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
                <span className="text-sm font-medium">{svc.name}</span>
                <Badge variant={svc.status === 'online' ? 'success' : 'danger'}>
                  {svc.status === 'online' ? 'Online' : 'Offline'}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
