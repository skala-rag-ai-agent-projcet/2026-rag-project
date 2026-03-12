from langchain_community.tools.tavily_search import TavilySearchResults
from config import TAVILY_API_KEY


def get_search_tool(max_results: int = 5) -> TavilySearchResults:
    return TavilySearchResults(
        max_results=max_results,
        tavily_api_key=TAVILY_API_KEY,
    )


def web_search(query: str, max_results: int = 5) -> str:
    """Perform a web search and return formatted results."""
    try:
        tool = get_search_tool(max_results)
        results = tool.invoke(query)
    except Exception as e:
        print(f"[웹검색] 검색 실패: {e}")
        return "(검색 결과 없음)"

    if not results:
        return "(검색 결과 없음)"

    # Tavily가 에러 문자열을 반환하는 경우 방어
    if isinstance(results, str):
        if "Error" in results or "error" in results:
            print(f"[웹검색] API 에러: {results[:100]}")
            return "(검색 결과 없음)"
        return results

    formatted = []
    for r in results:
        if isinstance(r, dict):
            url = r.get("url", "")
            content = r.get("content", "")
            formatted.append(f"- {content}\n  Source: {url}")
        elif isinstance(r, str):
            if len(r) > 5:  # 한 글자씩 분리된 에러 문자열 필터링
                formatted.append(f"- {r}")

    return "\n\n".join(formatted) if formatted else "(검색 결과 없음)"
