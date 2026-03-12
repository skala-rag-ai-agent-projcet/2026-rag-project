import json
from langchain_openai import ChatOpenAI
from tools.search import web_search
from prompts.templates import COMPETITOR_ANALYSIS_PROMPT
from config import LLM_MODEL


def competitor_analysis_node(state: dict) -> dict:
    """경쟁사 맵, 대체기술, 진입장벽 분석 (tech+market 결과 기반 + 웹검색)."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")
    core_tech = profile.get("core_technology", "")

    print(f"\n[경쟁사 분석] {name} 경쟁 환경 분석 중...")

    # tech_analysis, market_policy_analysis를 프롬프트에 직접 전달
    tech = state.get("tech_analysis", {})
    market = state.get("market_policy_analysis", {})

    tech_str = (
        json.dumps(tech, ensure_ascii=False, indent=2)
        if isinstance(tech, dict)
        else str(tech)
    )
    market_str = (
        json.dumps(market, ensure_ascii=False, indent=2)
        if isinstance(market, dict)
        else str(market)
    )

    # 웹 검색
    search_results = web_search(
        f"{name} competitors {core_tech} energy startups comparison market share",
        max_results=7,
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = COMPETITOR_ANALYSIS_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        tech_analysis=tech_str,
        market_policy_analysis=market_str,
        search_results=search_results,
    )

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        analysis = {"summary": content, "parse_error": True}

    # competitiveness_score 추출
    competitiveness_score = analysis.get("competitiveness_score", 5)
    if isinstance(competitiveness_score, str):
        try:
            competitiveness_score = int(competitiveness_score)
        except ValueError:
            competitiveness_score = 5

    print(f"[경쟁사 분석] {name} 완료 (경쟁력 점수: {competitiveness_score}/10)")

    return {
        "competitor_analysis": analysis,
        "competitiveness_score": competitiveness_score,
        "sources": [f"경쟁사 분석 웹검색: {name}"],
        "log": [f"경쟁사 분석 완료: {name} (경쟁력 {competitiveness_score}/10)"],
    }
