from functools import partial
from langgraph.graph import StateGraph, START, END
from graph.state import GraphState
from agents.startup_search import startup_search_node
from agents.domain_check import domain_check_node
from agents.tech_analysis import tech_analysis_node
from agents.market_policy import market_policy_node
from agents.competitor_analysis import competitor_analysis_node
from agents.investment_decision import investment_decision_node
from agents.evaluation_check import evaluation_check_node
from agents.report_writer import report_writer_node


# ── Policy gate (pass-through) ──────────────────────────────────────
def policy_gate_node(state: dict) -> dict:
    """Fan-in 노드: tech_analysis + market_policy 완료 후 policy_violation 확인."""
    violation = state.get("working", {}).get("policy_violation", False)
    reason = state.get("working", {}).get("policy_violation_reason", "해당 없음")
    name = state.get("current_startup", {}).get("company_profile", {}).get("company_name", "Unknown")

    if violation:
        print(f"\n[Policy Gate] ⚠️ {name}: 정책 위반 감지 — {reason}")
    else:
        print(f"\n[Policy Gate] ✓ {name}: 정책 위반 없음 → 경쟁사 분석 진행")

    return {"log": [f"Policy Gate: violation={violation}"]}


# ── Routing functions ────────────────────────────────────────────────
def route_after_domain_check(state: dict) -> list[str] | str:
    """도메인 확인 후 라우팅: 적합 → tech + market 병렬, 부적합 → 재탐색."""
    if state.get("current_startup", {}).get("pipeline_flags", {}).get("domain_check_passed", False):
        return ["tech_analysis", "market_policy"]

    log = state.get("log", [])
    domain_fail_count = sum(1 for entry in log if "부적합" in entry)
    if domain_fail_count >= 2:
        print("\n[라우터] 최대 재탐색 횟수 도달. 평가를 종료합니다.")
        return END
    print("\n[라우터] Energy 도메인 부적합. 스타트업을 재탐색합니다.")
    return "startup_search"


def route_after_policy_check(state: dict) -> str:
    """Policy gate 이후: 위반 → END, 정상 → competitor_analysis."""
    if state.get("working", {}).get("policy_violation", False):
        print("\n[라우터] 정책 위반으로 평가를 종료합니다.")
        return END
    return "competitor_analysis"


def route_after_evaluation_check(state: dict) -> str:
    """평가 검증 후 라우팅: 통과 → 보고서, 미통과 → 재평가 (최대 1회)."""
    if not state.get("working", {}).get("recheck_required", False):
        return "report_writer"
    log = state.get("log", [])
    recheck_count = sum(1 for entry in log if "재평가 필요" in entry)
    if recheck_count >= 2:
        print("\n[라우터] 최대 재평가 횟수 도달. 보고서 생성으로 진행합니다.")
        return "report_writer"
    print("\n[라우터] 평가 불충분. 재평가를 수행합니다.")
    return "investment_decision"


# ── Graph builder ────────────────────────────────────────────────────
def build_graph(retriever=None):
    """LangGraph 워크플로우 구축.

    Flow:
        START → startup_search → domain_check
          → [tech_analysis, market_policy] (2개 병렬)
            → policy_gate (fan-in)
              → policy_violation? → END
              → no → competitor_analysis (순차)
                → investment_decision → evaluation_check → report_writer → END
    """
    # RAG 사용 에이전트에 retriever 바인딩
    tech_node = partial(tech_analysis_node, retriever=retriever)
    market_node = partial(market_policy_node, retriever=retriever)
    invest_node = partial(investment_decision_node, retriever=retriever)

    graph = StateGraph(GraphState)

    # 노드 등록
    graph.add_node("startup_search", startup_search_node)
    graph.add_node("domain_check", domain_check_node)
    graph.add_node("tech_analysis", tech_node)
    graph.add_node("market_policy", market_node)
    graph.add_node("policy_gate", policy_gate_node)
    graph.add_node("competitor_analysis", competitor_analysis_node)
    graph.add_node("investment_decision", invest_node)
    graph.add_node("evaluation_check", evaluation_check_node)
    graph.add_node("report_writer", report_writer_node)

    # START → startup_search → domain_check
    graph.add_edge(START, "startup_search")
    graph.add_edge("startup_search", "domain_check")

    # domain_check → [tech_analysis, market_policy] 병렬 또는 재탐색/END
    graph.add_conditional_edges("domain_check", route_after_domain_check)

    # tech_analysis, market_policy → policy_gate (fan-in)
    graph.add_edge("tech_analysis", "policy_gate")
    graph.add_edge("market_policy", "policy_gate")

    # policy_gate → competitor_analysis 또는 END
    graph.add_conditional_edges(
        "policy_gate",
        route_after_policy_check,
        {
            "competitor_analysis": "competitor_analysis",
            END: END,
        },
    )

    # competitor_analysis → investment_decision
    graph.add_edge("competitor_analysis", "investment_decision")

    # investment_decision → evaluation_check
    graph.add_edge("investment_decision", "evaluation_check")

    # evaluation_check → report_writer (통과) 또는 investment_decision (재평가)
    graph.add_conditional_edges(
        "evaluation_check",
        route_after_evaluation_check,
        {
            "report_writer": "report_writer",
            "investment_decision": "investment_decision",
        },
    )

    # report_writer → END
    graph.add_edge("report_writer", END)

    return graph.compile()
