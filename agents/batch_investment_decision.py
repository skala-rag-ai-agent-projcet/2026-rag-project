import json

from langchain_openai import ChatOpenAI

from prompts.batch_templates import BATCH_INVESTMENT_DECISION_PROMPT
from config import LLM_MODEL, EVALUATION_CRITERIA, EVALUATION_MAX_SCORES, INVESTMENT_THRESHOLD


def _build_batch_criteria_description() -> str:
    """배치 모드 평가 항목 설명 (max_score 포함)."""
    lines = []
    for key, info in EVALUATION_CRITERIA.items():
        max_score = EVALUATION_MAX_SCORES[key]
        lines.append(f"- **{info['name']}** (max_score: {max_score}점): {info['points']}")
    return "\n".join(lines)


def _build_criteria_json_template() -> str:
    """프롬프트 내 JSON 템플릿 예시."""
    parts = []
    for key in EVALUATION_CRITERIA:
        ms = EVALUATION_MAX_SCORES[key]
        parts.append(
            f'        "{key}": {{"score": <0-{ms}>, "max_score": {ms}, '
            f'"reason": "평가 근거", "evidence": "구체적 근거 데이터/사실"}}'
        )
    return ",\n".join(parts)


def _calculate_total_score(criteria_scores: dict) -> int:
    """각 항목 score 합산 (만점 100). 범위 초과 시 클램핑."""
    total = 0
    for key in EVALUATION_CRITERIA:
        entry = criteria_scores.get(key, {})
        score = entry.get("score", 0)
        if isinstance(score, (int, float)):
            max_score = EVALUATION_MAX_SCORES[key]
            total += max(0, min(int(score), max_score))
    return total


def batch_investment_decision_node(state: dict) -> dict:
    """배치 모드 투자 판단: score/max_score 방식, invest/reject 이분법."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")

    print(f"\n[배치 투자판단] {name} 투자 평가 중...")

    tech = state.get("tech_analysis", {})
    market = state.get("market_policy_analysis", {})
    competitor = state.get("competitor_analysis", {})

    tech_str = json.dumps(tech, ensure_ascii=False, indent=2) if isinstance(tech, dict) else str(tech)
    market_str = json.dumps(market, ensure_ascii=False, indent=2) if isinstance(market, dict) else str(market)
    competitor_str = json.dumps(competitor, ensure_ascii=False, indent=2) if isinstance(competitor, dict) else str(competitor)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = BATCH_INVESTMENT_DECISION_PROMPT.format(
        startup_name=name,
        startup_profile=json.dumps(profile, ensure_ascii=False, indent=2),
        tech_analysis=tech_str,
        market_policy_analysis=market_str,
        competitor_analysis=competitor_str,
        criteria_description=_build_batch_criteria_description(),
        criteria_json_template=_build_criteria_json_template(),
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
        print(f"[배치 투자판단] JSON 파싱 실패. 기본값 사용.")
        result = {
            "criteria_scores": {
                k: {"score": 0, "max_score": EVALUATION_MAX_SCORES[k], "reason": "파싱 오류", "evidence": "N/A"}
                for k in EVALUATION_CRITERIA
            },
            "total_score": 0,
            "verdict": "reject",
            "investment_memo": "평가를 완료할 수 없습니다.",
        }

    criteria_scores = result.get("criteria_scores", {})

    # 서버 사이드: max_score 보정 + score 클램핑
    for key in EVALUATION_CRITERIA:
        entry = criteria_scores.setdefault(key, {})
        entry["max_score"] = EVALUATION_MAX_SCORES[key]
        score = entry.get("score", 0)
        if isinstance(score, (int, float)):
            entry["score"] = max(0, min(int(score), EVALUATION_MAX_SCORES[key]))
        else:
            entry["score"] = 0
        criteria_scores[key] = entry

    # 서버 사이드 총점 재계산 + 판정
    total_score = _calculate_total_score(criteria_scores)
    verdict = "invest" if total_score >= INVESTMENT_THRESHOLD else "reject"

    print(f"[배치 투자판단] {name}")
    print(f"  총점: {total_score} / 100")
    print(f"  판정: {verdict.upper()} (기준: {INVESTMENT_THRESHOLD})")
    for key, info in EVALUATION_CRITERIA.items():
        entry = criteria_scores.get(key, {})
        print(f"    {info['name']}: {entry.get('score', 0)}/{EVALUATION_MAX_SCORES[key]}")

    return {
        "criteria_scores": criteria_scores,
        "weighted_score": float(total_score),
        "verdict": verdict,
        "investment_memo": result.get("investment_memo", ""),
        "log": [f"배치 투자판단 완료: {name} — {verdict} ({total_score}점)"],
    }
