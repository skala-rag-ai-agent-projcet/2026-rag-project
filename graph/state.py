from __future__ import annotations

import copy
import operator
from typing import Annotated, TypedDict


def deep_merge(old: dict, new: dict) -> dict:
    """Recursive deep merge reducer for LangGraph Annotated[dict, deep_merge].

    Parallel branches return deltas; deep_merge merges them without data loss.
    """
    if not old:
        return copy.deepcopy(new) if new else {}
    if not new:
        return copy.deepcopy(old)

    result = copy.deepcopy(old)
    for key, value in new.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class GraphState(TypedDict, total=False):
    """통합 State — nested dict + deep_merge reducer.

    current_startup:
        metadata         — {question, status}
        company_profile  — 기업 기본 정보
        domain_classification — {is_energy_domain, reason, sub_domain}
        technology_analysis   — 기술 분석 결과
        market_policy_analysis — 시장/정책 분석 결과
        competition_analysis  — 경쟁사 분석 결과
        investment_decision   — {criteria_scores, weighted_score, verdict, investment_memo}
        score_validation      — 평가 검증 결과
        pipeline_flags        — {domain_check_passed, technology_done, market_policy_done,
                                 competition_done, investment_done, report_included}

    working:
        retry_count, validation_errors, policy_violation,
        policy_violation_reason, input_validation_passed, recheck_required

    outputs:
        aggregation_result, report_output_path
    """

    # ── Core (nested, deep-merged) ──────────────────────────────
    current_startup: Annotated[dict, deep_merge]
    working: Annotated[dict, deep_merge]
    outputs: Annotated[dict, deep_merge]

    # ── Append-only lists ───────────────────────────────────────
    sources: Annotated[list[str], operator.add]
    log: Annotated[list[str], operator.add]
    rag_grading_log: Annotated[list[str], operator.add]
    references: Annotated[list[str], operator.add]
