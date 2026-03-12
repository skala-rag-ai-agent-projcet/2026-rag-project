import json
from langchain_openai import ChatOpenAI
from prompts.templates import EVALUATION_CHECK_PROMPT
from config import LLM_MODEL


def evaluation_check_node(state: dict) -> dict:
    """투자 평가 지표 반영 여부 확인."""
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")
    criteria_scores = state.get("criteria_scores", {})
    weighted_score = state.get("weighted_score", 0.0)
    verdict = state.get("verdict", "hold")
    memo = state.get("investment_memo", "")

    print(f"\n[평가 검증] {name} 투자 평가 검증 중...")

    decision_summary = json.dumps(
        {
            "criteria_scores": criteria_scores,
            "weighted_score": weighted_score,
            "verdict": verdict,
            "investment_memo": memo,
        },
        ensure_ascii=False,
        indent=2,
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = EVALUATION_CHECK_PROMPT.format(
        investment_decision=decision_summary,
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
        result = {"evaluation_complete": False, "feedback": "검증 파싱 실패"}

    is_complete = result.get("evaluation_complete", False)
    feedback = result.get("feedback", "")

    print(f"[평가 검증] 완료 여부: {'✓ 통과' if is_complete else '✗ 재평가 필요'}")
    if not is_complete:
        print(f"  피드백: {feedback}")

    return {
        "recheck_required": not is_complete,
        "log": [f"평가 검증: {'통과' if is_complete else '재평가 필요'} — {feedback}"],
    }
