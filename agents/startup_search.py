import json
from langchain_openai import ChatOpenAI
from tools.search import web_search
from prompts.templates import STARTUP_SEARCH_PROMPT
from config import LLM_MODEL


def startup_search_node(state: dict) -> dict:
    """사용자 입력 스타트업명으로 기업 프로필 수집."""
    startup_name = state.get("current_startup", {}).get("metadata", {}).get("question", "")

    print(f"\n[스타트업 소싱] {startup_name} 검색 중...")

    search_results = web_search(
        f"{startup_name} 스타트업 기업정보 기술 투자 에너지", max_results=10
    )

    # 부정적/리스크 검색
    negative_search_results = web_search(
        f"{startup_name} 리스크 한계 실패 적자 논란", max_results=5
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = STARTUP_SEARCH_PROMPT.format(
        startup_name=startup_name,
        search_results=search_results,
        negative_search_results=negative_search_results,
    )

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        profile = json.loads(content)
    except json.JSONDecodeError:
        print("[스타트업 소싱] JSON 파싱 실패. 기본 프로필 생성.")
        profile = {
            "company_name": startup_name,
            "description": "프로필 수집 실패 — 웹 검색 결과를 기반으로 분석을 계속합니다.",
        }

    print(f"[스타트업 소싱] {profile.get('company_name', startup_name)} 프로필 수집 완료")

    return {
        "current_startup": {
            "company_profile": profile,
        },
        "sources": [f"Tavily 검색: {startup_name}"],
        "log": [f"스타트업 소싱 완료: {profile.get('company_name', startup_name)}"],
    }
