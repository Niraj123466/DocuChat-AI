"""LangGraph workflow definition for DocuChat-AI."""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from src.agents.evaluator_agent import evaluator_agent
from src.agents.retriver_agent import retriver_agent
from src.schemas.response_schema import ResponseSchema
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("workflow")

def evaluation_edge(state: ResponseSchema) -> str:
    """Evaluates whether to retry query or terminate workflow."""
    eval_state = state.get("evaluation_state")
    retries = state.get("retry_count", 0)

    if eval_state == "False" and retries < settings.MAX_RETRIES:
        logger.info(f"Conditional edge: Retrying query with feedback (attempt {retries + 1})")
        return "retriver_agent"

    logger.info("Conditional edge: Workflow successfully terminated or max retries reached")
    return END

# Build LangGraph StateGraph
graph = StateGraph(ResponseSchema)

graph.add_node("retriver_agent", retriver_agent)
graph.add_node("evaluator_agent", evaluator_agent)

graph.add_edge(START, "retriver_agent")
graph.add_edge("retriver_agent", "evaluator_agent")
graph.add_conditional_edges(
    "evaluator_agent",
    evaluation_edge,
    {
        "retriver_agent": "retriver_agent",
        END: END,
    },
)

workflow = graph.compile()

if __name__ == "__main__":
    initial_state = {
        "user_query": "What are the key highlights of the document?",
        "query_response": "",
        "evaluation_state": "",
        "retry_count": 0,
        "instruction": "",
    }
    final_state = workflow.invoke(initial_state)
    print("Final State:", final_state)
