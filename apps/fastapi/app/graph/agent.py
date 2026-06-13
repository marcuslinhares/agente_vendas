from collections.abc import Sequence
from typing import Any

from langgraph.graph import END, StateGraph

from app.graph.nodes.agent_followup import FollowUpAgentNode
from app.graph.nodes.agent_router import AgentRouterNode
from app.graph.nodes.agent_sales import SalesAgentNode
from app.graph.nodes.agent_support import SupportAgentNode
from app.graph.nodes.l3_search import L3SearchNode
from app.graph.nodes.memory_gate import MemoryGateNode
from app.graph.nodes.memory_hydrate import MemoryHydrateNode
from app.graph.nodes.parse_classify import ParseClassifyNode
from app.graph.nodes.post_process import PostProcessNode
from app.graph.state import AgentState


def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Register nodes
    nodes: Sequence[tuple[str, Any]] = [
        ("parse_classify", ParseClassifyNode),
        ("memory_hydrate", MemoryHydrateNode),
        ("memory_gate", MemoryGateNode),
        ("agent_router", AgentRouterNode),
        ("l3_search", L3SearchNode),
        ("sales_agent", SalesAgentNode),
        ("support_agent", SupportAgentNode),
        ("followup_agent", FollowUpAgentNode),
        ("post_process", PostProcessNode),
    ]
    for name, node_class in nodes:
        workflow.add_node(name, node_class().run)

    # Main flow
    workflow.set_entry_point("parse_classify")
    workflow.add_edge("parse_classify", "memory_hydrate")
    workflow.add_edge("memory_hydrate", "memory_gate")

    # Conditional: L3 only if gate triggers
    workflow.add_conditional_edges(
        "memory_gate",
        lambda state: "l3_search" if state.get("l3_triggered") else "agent_router",
        {"l3_search": "l3_search", "agent_router": "agent_router"},
    )
    workflow.add_edge("l3_search", "agent_router")

    # Router → specialist agent
    workflow.add_conditional_edges(
        "agent_router",
        lambda state: state.get("selected_agent", "sales_agent"),
        {
            "sales_agent": "sales_agent",
            "support_agent": "support_agent",
            "followup_agent": "followup_agent",
        },
    )

    # All specialists go to post_process
    for specialist in ["sales_agent", "support_agent", "followup_agent"]:
        workflow.add_edge(specialist, "post_process")
    workflow.add_edge("post_process", END)

    return workflow.compile()  # type: ignore[return-value]
