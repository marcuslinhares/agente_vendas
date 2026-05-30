from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes.parse_classify import ParseClassifyNode
from app.graph.nodes.memory_hydrate import MemoryHydrateNode
from app.graph.nodes.memory_gate import MemoryGateNode
from app.graph.nodes.l3_search import L3SearchNode
from app.graph.nodes.agent_execute import AgentExecuteNode
from app.graph.nodes.post_process import PostProcessNode


def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("parse_classify", ParseClassifyNode().run)
    workflow.add_node("memory_hydrate", MemoryHydrateNode().run)
    workflow.add_node("memory_gate", MemoryGateNode().run)
    workflow.add_node("l3_search", L3SearchNode().run)
    workflow.add_node("agent_execute", AgentExecuteNode().run)
    workflow.add_node("post_process", PostProcessNode().run)

    # Edges
    workflow.set_entry_point("parse_classify")
    workflow.add_edge("parse_classify", "memory_hydrate")
    workflow.add_edge("memory_hydrate", "memory_gate")

    # Conditional: L3 only if gate triggers
    workflow.add_conditional_edges(
        "memory_gate",
        lambda state: "l3_search" if state.get("l3_triggered") else "agent_execute",
        {"l3_search": "l3_search", "agent_execute": "agent_execute"},
    )
    workflow.add_edge("l3_search", "agent_execute")
    workflow.add_edge("agent_execute", "post_process")
    workflow.add_edge("post_process", END)

    return workflow.compile()
