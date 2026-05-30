import json

from app.tools.registry import ToolDef, ToolRegistry


async def _create_order(params: dict) -> str:
    from app.services.postgres import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO orders (customer_id, items, total, payment_method, status) "
        "VALUES ($1, $2::jsonb, $3, $4, 'pending') "
        "RETURNING id, total, status",
        params["customer_id"],
        json.dumps(params.get("items", [])),
        params.get("total", 0),
        params.get("payment_method", "pending"),
    )
    return f"Pedido #{row['id']} criado! Total: R$ {float(row['total']):.2f}. Status: {row['status']}"


async def _get_order_status(params: dict) -> str:
    from app.services.postgres import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT status, total, created_at FROM orders WHERE id = $1",
        params["order_id"],
    )
    if not row:
        return "Pedido não encontrado."
    return f"Status: {row['status']}. Total: R$ {float(row['total']):.2f}. Criado em: {row['created_at']}"


def register_orders_tools(registry: ToolRegistry) -> None:
    registry.register_core(ToolDef(
        name="create_order",
        description="Create a new order for a customer with items and payment method",
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
                "items": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of items with product_id and quantity",
                },
                "total": {"type": "number", "description": "Order total value"},
                "payment_method": {"type": "string", "description": "Payment method"},
            },
            "required": ["customer_id", "items", "total"],
        },
        is_idempotent=False,
        execute=_create_order,
    ))
    registry.register_core(ToolDef(
        name="get_order_status",
        description="Check the current status of an order by its ID",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "format": "uuid", "description": "Order ID"},
            },
            "required": ["order_id"],
        },
        is_idempotent=True,
        execute=_get_order_status,
    ))
