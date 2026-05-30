'use client';

import { useRouter, usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  MessageSquare,
  Package,
  Users,
  ShoppingCart,
  Wrench,
  Settings,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/conversations', label: 'Conversas', icon: MessageSquare },
  { href: '/products', label: 'Produtos', icon: Package },
  { href: '/customers', label: 'Clientes', icon: Users },
  { href: '/orders', label: 'Pedidos', icon: ShoppingCart },
  { href: '/tools', label: 'Tools', icon: Wrench },
  { href: '/settings', label: 'Configurações', icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  function handleLogout() {
    localStorage.removeItem('token');
    router.push('/login');
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r bg-white">
        <div className="flex h-16 items-center border-b px-6">
          <h1 className="text-lg font-bold text-blue-600">Agente Vendas</h1>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <button
                key={item.href}
                onClick={() => router.push(item.href)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100',
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="border-t p-4">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            <LogOut className="h-5 w-5" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
