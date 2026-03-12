from langchain_community.tools.tavily_search import TavilySearchResults
from config import TAVILY_API_KEY


def get_search_tool(max_results: int = 5) -> TavilySearchResults:
    return TavilySearchResults(
        max_results=max_results,
        tavily_api_key=TAVILY_API_KEY,
    )


def web_search(query: str, max_results: int = 5) -> str:
    """Perform a web search and return formatted results."""
    tool = get_search_tool(max_results)
    results = tool.invoke(query)

    if not results:
        return "(No search results found)"

    formatted = []
    for r in results:
        url = r.get("url", "")
        content = r.get("content", "")
        formatted.append(f"- {content}\n  Source: {url}")

    return "\n\n".join(formatted)
