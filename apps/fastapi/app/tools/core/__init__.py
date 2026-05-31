from app.tools.core.customers import register_customers_tools
from app.tools.core.orders import register_orders_tools
from app.tools.core.products import register_products_tools
from app.tools.registry import ToolRegistry


def register_all_core_tools(registry: ToolRegistry) -> None:
    register_products_tools(registry)
    register_orders_tools(registry)
    register_customers_tools(registry)
