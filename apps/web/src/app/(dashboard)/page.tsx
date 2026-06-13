"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageSquare, Users, ShoppingCart, TrendingUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

function useAuth() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    apiClient("/auth/me")
      .then(() => setReady(true))
      .catch(() => router.push("/login"));
  }, [router]);

  return ready;
}

export default function DashboardPage() {
  const isAuthenticated = useAuth();

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => apiClient<any[]>("/conversations"),
    enabled: isAuthenticated,
  });

  const { data: customers } = useQuery({
    queryKey: ["customers"],
    queryFn: () => apiClient<any[]>("/customers"),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) return null;

  const activeConversations =
    conversations?.filter((c: any) => c.status === "active").length || 0;
  const leadCount = customers?.length || 0;
  const orderCount = 0; // Will be fetched from /orders in production

  const stats = [
    {
      title: "Conversas Ativas",
      value: activeConversations,
      icon: MessageSquare,
      color: "blue",
    },
    { title: "Leads", value: leadCount, icon: Users, color: "green" },
    {
      title: "Pedidos Hoje",
      value: orderCount,
      icon: ShoppingCart,
      color: "orange",
    },
    {
      title: "Taxa de Conversão",
      value: "--%",
      icon: TrendingUp,
      color: "purple",
    },
  ];

  return (
    <div>
      <h2 className="mb-6 text-2xl font-bold">Dashboard</h2>
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const colorMap: Record<string, string> = {
            blue: "bg-blue-50 text-blue-600",
            green: "bg-green-50 text-green-600",
            orange: "bg-orange-50 text-orange-600",
            purple: "bg-purple-50 text-purple-600",
          };
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

      {conversations && conversations.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-4 text-lg font-semibold">Últimas Conversas</h3>
          <div className="space-y-3">
            {conversations.slice(0, 5).map((conv: any) => (
              <Card key={conv.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{conv.whatsappId}</p>
                    <p className="text-sm text-gray-500">
                      {conv.classification || "Sem classificação"}
                    </p>
                  </div>
                  <span className="text-sm text-gray-400">
                    {new Date(conv.updatedAt).toLocaleDateString("pt-BR")}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
