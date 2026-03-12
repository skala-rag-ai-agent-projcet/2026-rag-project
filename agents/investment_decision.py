import json
import statistics
from langchain_openai import ChatOpenAI
from rag.corrective_rag import corrective_retrieve
from prompts.templates import INVESTMENT_DECISION_PROMPT
from config import LLM_MODEL, EVALUATION_CRITERIA, INVESTMENT_THRESHOLD


def _build_criteria_description() -> str:
    """9개 평가 항목 설명 — 구조화 블록 (0-100 범위 기준 High/Medium/Low)."""
    blocks = []
    for i, (key, info) in enumerate(EVALUATION_CRITERIA.items(), 1):
        weight_pct = int(info["weight"] * 100)
        rubric = info.get("scoring_rubric", {})
        question = info.get("evaluation_question", "")

        block = f"""### {i}. {info['name']} (비중 {weight_pct}%)
- 평가 질문: {question}
- 점수 기준:
  - **High** (80-100점): {rubric.get('high', '')}
  - **Medium** (45-79점): {rubric.get('medium', '')}
  - **Low** (0-44점): {rubric.get('low', '')}
- 평가 포인트: {info['points']}"""
        blocks.append(block)

    return "\n\n".join(blocks)


def _calculate_weighted_score(criteria_scores: dict) -> float:
    """9개 항목 가중합 계산."""
    total = 0.0
    for key, info in EVALUATION_CRITERIA.items():
        score = criteria_scores.get(key, {}).get("score", 50)
        total += info["weight"] * score
    return round(total, 2)


def investment_decision_node(state: dict, retriever=None) -> dict:
    """9개 항목 가중합 투자 판단."""
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    name = profile.get("company_name", "Unknown")

    print(f"\n[투자 판단] {name} 투자 평가 중...")

    tech = cs.get("technology_analysis", {})
    market = cs.get("market_policy_analysis", {})
    competitor = cs.get("competition_analysis", {})

    tech_str = json.dumps(tech, ensure_ascii=False, indent=2) if isinstance(tech, dict) else str(tech)
    market_str = json.dumps(market, ensure_ascii=False, indent=2) if isinstance(market, dict) else str(market)
    competitor_str = json.dumps(competitor, ensure_ascii=False, indent=2) if isinstance(competitor, dict) else str(competitor)

    # RAG: 평가 기준표/투자 판단 지표 참조
    rag_context = ""
    rag_sources = []
    rag_log = []
    if retriever is not None:
        rag_query = "에너지 스타트업 투자 평가 기준 심사 지표 배터리 ESS"
        rag_context, rag_sources, rag_log = corrective_retrieve(
            retriever, rag_query, name
        )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = INVESTMENT_DECISION_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        tech_analysis=tech_str,
        market_policy_analysis=market_str,
        competitor_analysis=competitor_str,
        criteria_description=_build_criteria_description(),
        threshold=INVESTMENT_THRESHOLD,
        rag_context=rag_context if rag_context else "(내부 참고자료 없음)",
    )

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        print(f"[투자 판단] JSON 파싱 실패. 기본값 사용.")
        result = {
            "criteria_scores": {
                k: {"score": 50, "justification": "파싱 오류"} for k in EVALUATION_CRITERIA
            },
            "weighted_score": 50.0,
            "verdict": "reject",
            "investment_memo": "평가를 완료할 수 없습니다.",
        }

    criteria_scores = result.get("criteria_scores", {})

    # 서버사이드 보정: 균일 점수 패널티 (9항목 점수 편차 < 2이면 15% 감점)
    raw_scores = []
    for key in EVALUATION_CRITERIA:
        score = criteria_scores.get(key, {}).get("score", 50)
        if isinstance(score, (int, float)):
            raw_scores.append(float(score))

    if len(raw_scores) >= 2:
        score_stdev = statistics.stdev(raw_scores)
        if score_stdev < 2:
            print(f"  ⚠ 균일 점수 감지 (편차 {score_stdev:.1f} < 2). 15% 감점 적용.")
            for key in EVALUATION_CRITERIA:
                entry = criteria_scores.get(key, {})
                original = entry.get("score", 50)
                if isinstance(original, (int, float)):
                    entry["score"] = max(0, int(original * 0.85))

    # 서버 사이드 가중합 재계산 (정확성 보장)
    weighted_score = _calculate_weighted_score(criteria_scores)
    verdict = "invest" if weighted_score >= INVESTMENT_THRESHOLD else "reject"

    print(f"[투자 판단] {name}")
    print(f"  가중합 점수: {weighted_score:.1f} / 100")
    print(f"  판정: {verdict.upper()} (기준: {INVESTMENT_THRESHOLD})")
    for key, info in EVALUATION_CRITERIA.items():
        score = criteria_scores.get(key, {}).get("score", "N/A")
        print(f"    {info['name']}: {score}")

    return {
        "current_startup": {
            "investment_decision": {
                "criteria_scores": criteria_scores,
                "weighted_score": weighted_score,
                "verdict": verdict,
                "investment_memo": result.get("investment_memo", ""),
                "weakness_analysis": result.get("weakness_analysis", {}),
            },
            "pipeline_flags": {"investment_done": True},
        },
        "sources": rag_sources,
        "log": [f"투자 판단 완료: {name} — {verdict} ({weighted_score:.1f}점)"],
        "rag_grading_log": rag_log,
    }
