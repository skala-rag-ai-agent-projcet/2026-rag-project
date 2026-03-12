from functools import partial

from langgraph.graph import StateGraph, START, END

from graph.state import GraphState
from agents.startup_search import startup_search_node
from agents.tech_analysis import tech_analysis_node
from agents.market_policy import market_policy_node
from agents.batch_competitor_analysis import batch_competitor_node
from agents.batch_input_validation import batch_input_validation_node
from agents.batch_investment_decision import batch_investment_decision_node
from agents.batch_evaluation_check import batch_evaluation_check_node


# ── Fan-in node ──────────────────────────────────────────────────────
def _batch_fan_in_node(state: dict) -> dict:
    """Fan-in: tech_analysis + market_policy 완료 후 pipeline_flags 확인 + 상태 검증."""
    cs = state.get("current_startup", {})
    flags = cs.get("pipeline_flags", {})
    name = cs.get("company_profile", {}).get("company_name", "Unknown")
    violation = state.get("working", {}).get("policy_violation", False)

    tech_done = flags.get("technology_done", False)
    market_done = flags.get("market_policy_done", False)

    if not tech_done:
        print(f"\n[Batch Fan-in] ⚠️ {name}: 기술 분석 미완료")
    if not market_done:
        print(f"\n[Batch Fan-in] ⚠️ {name}: 시장/정책 분석 미완료")

    if violation:
        print(f"\n[Batch Fan-in] ⚠️ {name}: 정책 위반 감지")
    else:
        print(f"\n[Batch Fan-in] ✓ {name}: 분석 결과 수집 완료")

    return {"log": [f"Batch fan-in: violation={violation}, tech={tech_done}, market={market_done}"]}


# ── Aggregation node ─────────────────────────────────────────────────
def batch_aggregation_node(state: dict) -> dict:
    """current_startup → outputs.aggregation_result canonical 변환."""
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    inv = cs.get("investment_decision", {})
    comp = cs.get("competition_analysis", {})

    canonical = {
        "company_name": profile.get("company_name", "Unknown"),
        "domain_classification": profile.get("domain_classification", ""),
        "core_technology": profile.get("core_technology", ""),
        "total_score": int(inv.get("weighted_score", 0)),
        "verdict": inv.get("verdict", "reject"),
        "criteria_scores": inv.get("criteria_scores", {}),
        "investment_memo": inv.get("investment_memo", ""),
        "policy_violation": state.get("working", {}).get("policy_violation", False),
        "policy_violation_reason": state.get("working", {}).get("policy_violation_reason", ""),
        "competitor_analyzed": comp.get("analyzed", False) if isinstance(comp, dict) else False,
        "competitiveness_score": comp.get("competitiveness_score") if isinstance(comp, dict) else None,
    }

    name = profile.get("company_name", "Unknown")
    print(f"\n[배치 집계] {name}: canonical 결과 생성 완료")

    return {
        "outputs": {
            "aggregation_result": canonical,
        },
        "log": [f"배치 집계 완료: {name}"],
    }


# ── Routing functions ────────────────────────────────────────────────
def route_after_input_validation(state: dict) -> str:
    """입력 검증 후 라우팅.

    통과 → batch_investment_decision
    실패 → batch_competitor 재시도 (max 1회, 이후 강제 진행)
    """
    if state.get("working", {}).get("input_validation_passed", False):
        return "batch_investment_decision"

    log = state.get("log", [])
    fail_count = sum(1 for e in log if "input_validation 실패" in e)

    if fail_count >= 2:
        print("\n[라우터] 입력 검증 2회 실패. 투자 판단으로 강제 진행.")
        return "batch_investment_decision"

    print("\n[라우터] 입력 검증 실패. 경쟁사 분석을 재시도합니다.")
    return "batch_competitor"


def route_after_batch_eval(state: dict) -> str:
    """평가 검증 후 라우팅.

    통과 → batch_aggregation
    실패 → batch_investment_decision 재시도 (max 1회, 이후 집계)
    """
    if not state.get("working", {}).get("recheck_required", False):
        return "batch_aggregation"

    log = state.get("log", [])
    fail_count = sum(1 for e in log if "evaluation_check 실패" in e)

    if fail_count >= 2:
        print("\n[라우터] 평가 검증 2회 실패. 집계로 진행합니다.")
        return "batch_aggregation"

    print("\n[라우터] 평가 검증 실패. 투자 판단을 재시도합니다.")
    return "batch_investment_decision"


# ── Graph builder ────────────────────────────────────────────────────
def build_batch_graph(retriever=None):
    """배치 모드 per-startup LangGraph 워크플로우.

    Flow:
        START → startup_search → [tech_analysis, market_policy] (병렬)
          → batch_fan_in → batch_competitor
            → batch_input_validation
              → fail → batch_competitor (재시도, max 1)
              → pass → batch_investment_decision
                → batch_evaluation_check
                  → fail → batch_investment_decision (재시도, max 1)
                  → pass → batch_aggregation → END
    """
    tech_node = partial(tech_analysis_node, retriever=retriever)
    market_node = partial(market_policy_node, retriever=retriever)
    invest_node = partial(batch_investment_decision_node, retriever=retriever)

    graph = StateGraph(GraphState)

    # 노드 등록
    graph.add_node("startup_search", startup_search_node)
    graph.add_node("tech_analysis", tech_node)
    graph.add_node("market_policy", market_node)
    graph.add_node("batch_fan_in", _batch_fan_in_node)
    graph.add_node("batch_competitor", batch_competitor_node)
    graph.add_node("batch_input_validation", batch_input_validation_node)
    graph.add_node("batch_investment_decision", invest_node)
    graph.add_node("batch_evaluation_check", batch_evaluation_check_node)
    graph.add_node("batch_aggregation", batch_aggregation_node)

    # START → startup_search
    graph.add_edge(START, "startup_search")

    # startup_search → [tech_analysis, market_policy] 병렬
    graph.add_edge("startup_search", "tech_analysis")
    graph.add_edge("startup_search", "market_policy")

    # tech_analysis, market_policy → batch_fan_in (fan-in)
    graph.add_edge("tech_analysis", "batch_fan_in")
    graph.add_edge("market_policy", "batch_fan_in")

    # batch_fan_in → batch_competitor
    graph.add_edge("batch_fan_in", "batch_competitor")

    # batch_competitor → batch_input_validation
    graph.add_edge("batch_competitor", "batch_input_validation")

    # batch_input_validation → routing
    graph.add_conditional_edges(
        "batch_input_validation",
        route_after_input_validation,
        {
            "batch_investment_decision": "batch_investment_decision",
            "batch_competitor": "batch_competitor",
        },
    )

    # batch_investment_decision → batch_evaluation_check
    graph.add_edge("batch_investment_decision", "batch_evaluation_check")

    # batch_evaluation_check → routing
    graph.add_conditional_edges(
        "batch_evaluation_check",
        route_after_batch_eval,
        {
            "batch_investment_decision": "batch_investment_decision",
            "batch_aggregation": "batch_aggregation",
        },
    )

    # batch_aggregation → END
    graph.add_edge("batch_aggregation", END)

    return graph.compile()
