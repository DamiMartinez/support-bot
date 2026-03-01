"""RAG tool: search the knowledge base for relevant policy/info passages."""

from google.adk.tools import ToolContext

from support_bot.storage.knowledge_base import get_kb_chunks, search_knowledge_base_local


def search_knowledge_base(query: str, tool_context: ToolContext) -> dict:
    """Search the support knowledge base for information relevant to the customer's question.

    Use this tool when the customer asks about:
    - Return or refund policies
    - Shipping times or tracking
    - How to resolve common issues (damaged item, wrong item, etc.)
    - Escalation or contact procedures

    Args:
        query: A natural-language question or keyword describing what to look up.

    Returns:
        A dict with 'results' (list of passages) and 'count' (int).
    """
    chunks = get_kb_chunks()
    if not chunks:
        return {
            "results": [],
            "count": 0,
            "message": "Knowledge base is empty or could not be loaded.",
        }

    hits = search_knowledge_base_local(query, chunks, top_k=3)
    passages = [
        {
            "source": chunk.source,
            "heading": chunk.heading,
            "content": chunk.content,
        }
        for chunk in hits
    ]

    return {
        "results": passages,
        "count": len(passages),
        "message": f"Found {len(passages)} relevant passage(s).",
    }
