import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Agente de Vendas - CRM',
  description: 'CRM para gestão de conversas e vendas WhatsApp',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
