from config import EVALUATION_CRITERIA, EVALUATION_MAX_SCORES


def batch_evaluation_check_node(state: dict) -> dict:
    """배치 모드 평가 검증 (rule-based, LLM 미사용).

    검증 항목:
      1. 9개 항목 모두 존재
      2. 0 <= score <= max_score
      3. total == sum(scores)
      4. verdict in {invest, reject}
    """
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    name = profile.get("company_name", "Unknown")

    inv = cs.get("investment_decision", {})
    criteria_scores = inv.get("criteria_scores", {})
    weighted_score = inv.get("weighted_score", 0.0)
    verdict = inv.get("verdict", "")

    print(f"\n[배치 평가검증] {name} 투자 판단 검증 중...")

    errors: list[str] = []
    required_keys = list(EVALUATION_CRITERIA.keys())

    # 1. 9개 항목 존재 확인
    for key in required_keys:
        if key not in criteria_scores:
            errors.append(f"항목 누락: {key}")

    # 2. 0 <= score <= max_score
    for key in required_keys:
        entry = criteria_scores.get(key, {})
        score = entry.get("score")
        max_score = EVALUATION_MAX_SCORES.get(key, 0)
        if score is None:
            errors.append(f"{key}: score 없음")
        elif not isinstance(score, (int, float)):
            errors.append(f"{key}: score가 숫자가 아님 ({score})")
        elif score < 0 or score > max_score:
            errors.append(f"{key}: score={score}, 범위 초과 (0~{max_score})")

    # 3. total == sum(scores)
    expected_total = sum(
        criteria_scores.get(key, {}).get("score", 0)
        for key in required_keys
        if isinstance(criteria_scores.get(key, {}).get("score", 0), (int, float))
    )
    if abs(weighted_score - expected_total) > 1:
        errors.append(f"총점 불일치: weighted_score={weighted_score}, 합산={expected_total}")

    # 4. verdict in {invest, reject}
    if verdict not in ("invest", "reject"):
        errors.append(f"verdict 부적절: '{verdict}' (invest/reject만 허용)")

    recheck = len(errors) > 0

    if not recheck:
        print(f"[배치 평가검증] {name}: ✓ 검증 통과")
    else:
        print(f"[배치 평가검증] {name}: ✗ 재평가 필요 ({len(errors)}건)")
        for e in errors:
            print(f"  - {e}")

    return {
        "working": {
            "recheck_required": recheck,
            "validation_errors": errors,
        },
        "log": [
            f"evaluation_check {'통과' if not recheck else '실패'}: {name}"
            + (f" ({', '.join(errors)})" if errors else "")
        ],
    }
