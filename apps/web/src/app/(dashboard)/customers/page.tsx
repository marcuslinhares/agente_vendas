"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search } from "lucide-react";

const classColors: Record<
  string,
  "success" | "warning" | "danger" | "default"
> = {
  lead_quente: "success",
  lead_morno: "warning",
  lead_frio: "danger",
  cliente: "default",
};

const classLabels: Record<string, string> = {
  lead_quente: "🔥 Quente",
  lead_morno: "⚡ Morno",
  lead_frio: "❄️ Frio",
  cliente: "⭐ Cliente",
};

export default function CustomersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const { data: customers, isLoading } = useQuery({
    queryKey: ["customers"],
    queryFn: () => apiClient<any[]>("/customers"),
  });

  const classifyMutation = useMutation({
    mutationFn: ({
      conversationId,
      classification,
    }: {
      conversationId: string;
      classification: string;
    }) =>
      apiClient("/customers/classify", {
        method: "POST",
        body: JSON.stringify({ conversationId, classification }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["customers"] }),
  });

  const filtered = customers?.filter(
    (c: any) =>
      c.name?.toLowerCase().includes(search.toLowerCase()) ||
      c.whatsappId?.includes(search),
  );

  function cycleClassification(customer: any) {
    const order = ["lead_frio", "lead_morno", "lead_quente", "cliente"];
    const currentIndex = order.indexOf(customer.classification);
    const next = order[(currentIndex + 1) % order.length];
    classifyMutation.mutate({
      conversationId: customer.id,
      classification: next,
    });
  }

  if (isLoading) return <div className="p-8">Carregando...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold">Clientes</h2>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Buscar por nome ou whatsapp..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                Nome
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                WhatsApp
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                Classificação
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                Último Contato
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered?.map((customer: any) => (
              <tr key={customer.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">
                  {customer.name || "—"}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  {customer.whatsappId}
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => cycleClassification(customer)}>
                    <Badge
                      variant={
                        classColors[customer.classification] || "default"
                      }
                    >
                      {classLabels[customer.classification] ||
                        "Sem classificação"}
                    </Badge>
                  </button>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {customer.lastContactAt
                    ? new Date(customer.lastContactAt).toLocaleDateString(
                        "pt-BR",
                      )
                    : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cycleClassification(customer)}
                    disabled={classifyMutation.isPending}
                  >
                    Alterar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered?.length === 0 && (
          <p className="py-8 text-center text-gray-500">
            Nenhum cliente encontrado
          </p>
        )}
      </div>
    </div>
  );
}
