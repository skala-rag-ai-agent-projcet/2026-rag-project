from agents.competitor_analysis import competitor_analysis_node


def batch_competitor_node(state: dict) -> dict:
    """배치 모드 경쟁사 분석: policy_violation 시 skip, 아니면 기존 로직 위임."""
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    name = profile.get("company_name", "Unknown")

    if state.get("working", {}).get("policy_violation", False):
        reason = state.get("working", {}).get("policy_violation_reason", "정책 위반")
        print(f"\n[배치 경쟁사] {name}: 정책 위반으로 경쟁사 분석 생략")
        return {
            "current_startup": {
                "competition_analysis": {
                    "analyzed": False,
                    "skip_reason": reason,
                    "rank_score": None,
                },
            },
            "log": [f"배치 경쟁사 분석 생략: {name} (사유: {reason})"],
        }

    # 정상 케이스: 기존 competitor_analysis_node 위임
    result = competitor_analysis_node(state)

    # analyzed=True 추가
    comp = result.get("current_startup", {}).get("competition_analysis", {})
    comp["analyzed"] = True
    result["current_startup"]["competition_analysis"] = comp

    return result
