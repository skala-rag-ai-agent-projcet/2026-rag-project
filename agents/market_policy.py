import json
from langchain_openai import ChatOpenAI
from rag.corrective_rag import corrective_retrieve
from tools.search import web_search
from prompts.templates import MARKET_POLICY_PROMPT
from config import LLM_MODEL


def market_policy_node(state: dict, retriever=None) -> dict:
    """시장 규모, 정책 수혜, 규제 리스크 분석 (Corrective RAG + 웹검색) + policy_violation 판별."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")
    domain_class = profile.get("domain_classification", "에너지")

    print(f"\n[시장/정책 분석] {name} 시장 분석 중...")

    # Corrective RAG 검색
    rag_query = f"{domain_class} 에너지 시장 규모 성장 정책 TAM SAM"
    rag_context, rag_sources, rag_log = corrective_retrieve(
        retriever, rag_query, name
    )

    # 웹 검색
    search_results = web_search(
        f"{name} {domain_class} market size TAM growth policy IRA 2024 2025",
        max_results=7,
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = MARKET_POLICY_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        rag_context=rag_context,
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

    # policy_violation 추출
    policy_violation = analysis.get("policy_violation", False)
    policy_violation_reason = analysis.get(
        "policy_violation_reason", "해당 없음"
    )

    if policy_violation:
        print(f"[시장/정책 분석] ⚠️ 정책 위반 감지: {policy_violation_reason}")

    print(f"[시장/정책 분석] {name} 완료")

    return {
        "market_policy_analysis": analysis,
        "policy_violation": policy_violation,
        "policy_violation_reason": policy_violation_reason,
        "sources": [f"시장/정책 분석 웹검색: {name}"] + rag_sources,
        "log": [f"시장/정책 분석 완료: {name}"],
        "rag_grading_log": rag_log,
    }
