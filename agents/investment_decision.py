import json
from langchain_openai import ChatOpenAI
from prompts.templates import INVESTMENT_DECISION_PROMPT
from config import LLM_MODEL, EVALUATION_CRITERIA, INVESTMENT_THRESHOLD


def _build_criteria_description() -> str:
    """9개 평가 항목 설명 포맷팅."""
    lines = []
    for key, info in EVALUATION_CRITERIA.items():
        weight_pct = int(info["weight"] * 100)
        lines.append(f"- **{info['name']}** (비중 {weight_pct}%): {info['points']}")
    return "\n".join(lines)


def _calculate_weighted_score(criteria_scores: dict) -> float:
    """9개 항목 가중합 계산."""
    total = 0.0
    for key, info in EVALUATION_CRITERIA.items():
        score = criteria_scores.get(key, {}).get("score", 50)
        total += info["weight"] * score
    return round(total, 2)


def investment_decision_node(state: dict) -> dict:
    """9개 항목 가중합 투자 판단."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")

    print(f"\n[투자 판단] {name} 투자 평가 중...")

    tech = state.get("tech_analysis", {})
    market = state.get("market_policy_analysis", {})
    competitor = state.get("competitor_analysis", {})

    tech_str = json.dumps(tech, ensure_ascii=False, indent=2) if isinstance(tech, dict) else str(tech)
    market_str = json.dumps(market, ensure_ascii=False, indent=2) if isinstance(market, dict) else str(market)
    competitor_str = json.dumps(competitor, ensure_ascii=False, indent=2) if isinstance(competitor, dict) else str(competitor)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = INVESTMENT_DECISION_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        tech_analysis=tech_str,
        market_policy_analysis=market_str,
        competitor_analysis=competitor_str,
        criteria_description=_build_criteria_description(),
        threshold=INVESTMENT_THRESHOLD,
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
            "verdict": "hold",
            "investment_memo": "평가를 완료할 수 없습니다.",
        }

    criteria_scores = result.get("criteria_scores", {})

    # 서버 사이드 가중합 재계산 (정확성 보장)
    weighted_score = _calculate_weighted_score(criteria_scores)
    verdict = "invest" if weighted_score >= INVESTMENT_THRESHOLD else "hold"

    print(f"[투자 판단] {name}")
    print(f"  가중합 점수: {weighted_score:.1f} / 100")
    print(f"  판정: {verdict.upper()} (기준: {INVESTMENT_THRESHOLD})")
    for key, info in EVALUATION_CRITERIA.items():
        score = criteria_scores.get(key, {}).get("score", "N/A")
        print(f"    {info['name']}: {score}")

    return {
        "criteria_scores": criteria_scores,
        "weighted_score": weighted_score,
        "verdict": verdict,
        "investment_memo": result.get("investment_memo", ""),
        "log": [f"투자 판단 완료: {name} — {verdict} ({weighted_score:.1f}점)"],
    }
