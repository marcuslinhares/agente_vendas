from app.tools.registry import ToolDef, ToolRegistry


async def _get_products(params: dict) -> str:
    from app.services.postgres import get_pool

    pool = await get_pool()
    category = params.get("category")
    search = params.get("search", "")
    page = params.get("page", 1)
    limit = params.get("limit", 10)
    offset = (page - 1) * limit

    if category and search:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE category = $1 AND name ILIKE $2 AND is_active = true "
            "ORDER BY name LIMIT $3 OFFSET $4",
            category, f"%{search}%", limit, offset,
        )
    elif category:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE category = $1 AND is_active = true "
            "ORDER BY name LIMIT $2 OFFSET $3",
            category, limit, offset,
        )
    elif search:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE name ILIKE $1 AND is_active = true "
            "ORDER BY name LIMIT $2 OFFSET $3",
            f"%{search}%", limit, offset,
        )
    else:
        rows = await pool.fetch(
            "SELECT name, description, price, category, stock, image_url "
            "FROM products WHERE is_active = true "
            "ORDER BY name LIMIT $1 OFFSET $2",
            limit, offset,
        )

    if not rows:
        return "Nenhum produto encontrado."

    result = []
    for r in rows:
        result.append(
            f"- {r['name']}: R$ {float(r['price']):.2f} "
            f"({r['stock']} em estoque) - {str(r['description'] or '')[:100]}"
        )
    return "\n".join(result)


async def _check_stock(params: dict) -> str:
    from app.services.postgres import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT name, stock, price FROM products WHERE id = $1 AND is_active = true",
        params["product_id"],
    )
    if not row:
        return "Produto não encontrado."
    return f"{row['name']}: {row['stock']} unidades em estoque. Preço: R$ {float(row['price']):.2f}"


def register_products_tools(registry: ToolRegistry) -> None:
    registry.register_core(ToolDef(
        name="get_products",
        description="List products available in the catalog with optional filters by category or search term",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Product category filter"},
                "search": {"type": "string", "description": "Search term in product name"},
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 10},
            },
        },
        is_idempotent=True,
        execute=_get_products,
    ))
    registry.register_core(ToolDef(
        name="check_stock",
        description="Check stock availability for a specific product by its ID",
        parameters={
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "format": "uuid", "description": "Product ID"},
            },
            "required": ["product_id"],
        },
        is_idempotent=True,
        execute=_check_stock,
    ))
