def batch_input_validation_node(state: dict) -> dict:
    """배치 모드 입력 검증 (rule-based, LLM 미사용).

    검증 항목:
      1. tech_analysis 완료 여부 + 필수 필드
      2. market_policy_analysis 완료 여부 + 필수 필드
      3. competitor_analysis 완료 또는 skip 여부
      4. startup_profile 필수 필드
    """
    errors: list[str] = []
    profile = state.get("startup_profile", {})
    name = profile.get("company_name", "Unknown")

    print(f"\n[배치 입력검증] {name} 입력 데이터 검증 중...")

    # 1. tech_analysis
    tech = state.get("tech_analysis", {})
    if not tech or not isinstance(tech, dict):
        errors.append("tech_analysis 누락")
    elif tech.get("parse_error"):
        errors.append("tech_analysis 파싱 오류")
    else:
        for field in ("core_technology", "trl_level", "summary"):
            if not tech.get(field):
                errors.append(f"tech_analysis.{field} 누락")

    # 2. market_policy_analysis
    market = state.get("market_policy_analysis", {})
    if not market or not isinstance(market, dict):
        errors.append("market_policy_analysis 누락")
    else:
        for field in ("tam", "summary"):
            if not market.get(field):
                errors.append(f"market_policy_analysis.{field} 누락")

    # 3. competitor_analysis (완료 or skip)
    comp = state.get("competitor_analysis", {})
    if not comp or not isinstance(comp, dict):
        errors.append("competitor_analysis 누락")
    elif "analyzed" not in comp:
        errors.append("competitor_analysis.analyzed 필드 누락")

    # 4. startup_profile 필수 필드
    if not profile.get("company_name"):
        errors.append("startup_profile.company_name 누락")

    passed = len(errors) == 0

    if passed:
        print(f"[배치 입력검증] {name}: ✓ 검증 통과")
    else:
        print(f"[배치 입력검증] {name}: ✗ 검증 실패 ({len(errors)}건)")
        for e in errors:
            print(f"  - {e}")

    return {
        "input_validation_passed": passed,
        "validation_errors": errors,
        "log": [
            f"input_validation {'통과' if passed else '실패'}: {name}"
            + (f" ({', '.join(errors)})" if errors else "")
        ],
    }
