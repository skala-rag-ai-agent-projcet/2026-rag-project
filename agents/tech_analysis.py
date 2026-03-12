import json
from langchain_openai import ChatOpenAI
from rag.corrective_rag import corrective_retrieve
from tools.search import web_search
from prompts.templates import TECH_ANALYSIS_PROMPT
from config import LLM_MODEL


def tech_analysis_node(state: dict, retriever=None) -> dict:
    """에너지 특화 기술 심층 분석 (Corrective RAG + 웹검색)."""
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    name = profile.get("company_name", "Unknown")
    core_tech = profile.get("core_technology", "")

    print(f"\n[기술 분석] {name} 기술 분석 중...")

    # Corrective RAG 검색
    rag_query = f"{name} {core_tech} 에너지 기술 배터리 ESS 효율"
    rag_context, rag_sources, rag_log = corrective_retrieve(
        retriever, rag_query, name
    )

    # 웹 검색
    search_results = web_search(
        f"{name} {core_tech} technology energy battery performance specifications",
        max_results=7,
    )

    # 부정적/리스크 검색
    negative_search_results = web_search(
        f"{name} {core_tech} 한계 문제 실패 기술결함 리콜", max_results=5
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = TECH_ANALYSIS_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        rag_context=rag_context,
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
        analysis = json.loads(content)
    except json.JSONDecodeError:
        analysis = {"summary": content, "parse_error": True}

    print(f"[기술 분석] {name} 완료")

    return {
        "current_startup": {
            "technology_analysis": analysis,
            "pipeline_flags": {"technology_done": True},
        },
        "sources": [f"기술 분석 웹검색: {name}"] + rag_sources,
        "log": [f"기술 분석 완료: {name}"],
        "rag_grading_log": rag_log,
    }
