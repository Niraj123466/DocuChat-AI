"""Generates Mermaid diagram definition from the LangGraph workflow."""
from __future__ import annotations

from src.Workflow.workflow import workflow

def generate_mermaid() -> str:
    """Extracts Mermaid graph definition from the compiled LangGraph workflow."""
    return workflow.get_graph().draw_mermaid()

if __name__ == "__main__":
    mermaid_text = generate_mermaid()
    print(mermaid_text)