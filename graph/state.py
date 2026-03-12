from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class GraphState(TypedDict, total=False):
    """통합 State — 모든 에이전트가 공유하는 상태."""

    # Base
    question: str                                       # 사용자 입력 (스타트업명)
    sources: Annotated[list[str], operator.add]          # 출처 누적
    log: Annotated[list[str], operator.add]              # 로그 누적
    status: Literal["pending", "completed", "failed", "retry"]

    # Sourcing + Domain Check
    startup_profile: dict                                # 기업 기본 정보
    domain_fit: bool                                     # Energy 도메인 여부
    domain_fit_reason: str

    # Analysis (각 에이전트 결과)
    tech_analysis: dict                                  # 기술 분석
    market_policy_analysis: dict                         # 시장/정책 분석
    competitor_analysis: dict                            # 경쟁사 분석

    # Corrective RAG / Policy gate
    policy_violation: bool                               # 정책 위반 여부
    policy_violation_reason: str                         # 위반 사유
    competitiveness_score: int                           # 경쟁력 점수 0-10
    rag_grading_log: Annotated[list[str], operator.add]  # CRAG 그레이딩 로그

    # Decision
    criteria_scores: dict                                # 9개 항목 점수
    weighted_score: float                                # 가중합
    verdict: Literal["invest", "hold", "reject"]
    recheck_required: bool                               # 지표 반영 재확인
    investment_memo: str

    # Report
    investment_report: str                               # PDF 경로
    references: Annotated[list[str], operator.add]       # 출처 누적
