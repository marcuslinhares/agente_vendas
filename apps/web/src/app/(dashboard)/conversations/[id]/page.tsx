'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Send, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ConversationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: conversation, isLoading } = useQuery({
    queryKey: ['conversation', params.id],
    queryFn: () => apiClient<any>(`/conversations/${params.id}`),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || sending) return;

    setSending(true);
    try {
      await apiClient(`/conversations/${params.id}/send`, {
        method: 'POST',
        body: JSON.stringify({ text: message }),
      });
      setMessage('');
      queryClient.invalidateQueries({ queryKey: ['conversation', params.id] });
    } catch (err) {
      console.error('Failed to send:', err);
    } finally {
      setSending(false);
    }
  }

  if (isLoading) return <div className="p-8">Carregando...</div>;
  if (!conversation) return <div className="p-8">Conversa não encontrada</div>;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="flex items-center gap-4 border-b bg-white p-4">
        <button onClick={() => router.back()} className="rounded-full p-2 hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="font-semibold">{conversation.whatsappId}</h2>
          <div className="flex gap-2">
            {conversation.classification && (
              <Badge variant="warning">{conversation.classification}</Badge>
            )}
            <Badge variant="default">{conversation.status}</Badge>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {conversation.messages?.map((msg: any) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}
          >
            <div
              className={`max-w-[70%] rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-gray-100 text-gray-900'
                  : 'bg-blue-600 text-white'
              }`}
            >
              <p className="text-sm">{msg.content}</p>
              <p className="mt-1 text-right text-xs opacity-70">
                {new Date(msg.createdAt).toLocaleTimeString('pt-BR')}
              </p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex gap-3 border-t bg-white p-4">
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Digite sua mensagem..."
          className="flex-1"
        />
        <Button type="submit" disabled={sending || !message.trim()}>
          <Send className="mr-2 h-4 w-4" />
          {sending ? 'Enviando...' : 'Enviar'}
        </Button>
      </form>
    </div>
  );
}
