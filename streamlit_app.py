import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from graph.state import deep_merge

st.set_page_config(
    page_title="AI 스타트업 투자 평가 에이전트",
    page_icon="⚡",
    layout="wide",
)

# --- Sidebar ---
with st.sidebar:
    st.title("⚡ 투자 평가 에이전트")
    st.markdown("Energy 도메인 스타트업 투자 평가")
    st.divider()

    st.subheader("설정")
    from config import DOMAIN, INVESTMENT_THRESHOLD, EVALUATION_CRITERIA

    st.metric("도메인", DOMAIN)
    st.metric("투자 기준점수", f"{INVESTMENT_THRESHOLD}")

    st.divider()

    # 모드 선택
    mode = st.radio("평가 모드", ["Single", "Batch"], horizontal=True)

    st.divider()
    st.subheader("9개 평가 항목")
    for key, info in EVALUATION_CRITERIA.items():
        weight_pct = int(info["weight"] * 100)
        st.caption(f"**{info['name']}** ({weight_pct}%)")


# --- RAG Init (cached) ---
@st.cache_resource(show_spinner="RAG 벡터스토어 구축 중...")
def init_rag():
    from rag.retriever import build_vectorstore, get_retriever
    vs = build_vectorstore()
    return get_retriever(vs)


# --- Main ---
st.title("AI 스타트업 투자 평가 에이전트")
st.caption("Energy 도메인 스타트업에 대한 심층 투자 평가를 수행합니다.")


def run_single_evaluation(startup_name: str, retriever, show_progress=True):
    """단일 스타트업 평가 실행 → final_state 반환."""
    from graph.workflow import build_graph
    app = build_graph(retriever=retriever)

    initial_state = {
        "current_startup": {
            "metadata": {"question": startup_name, "status": "pending"},
        },
        "sources": [],
        "log": [],
        "rag_grading_log": [],
    }

    if show_progress:
        progress_bar = st.progress(0, text="파이프라인 시작...")

    final_state = None

    with st.spinner(f"{startup_name} 투자 평가 진행 중..."):
        for event in app.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                if show_progress:
                    if node_name == "startup_search":
                        progress_bar.progress(10, text="스타트업 소싱 완료")
                    elif node_name == "domain_check":
                        progress_bar.progress(20, text="도메인 확인 완료")
                    elif node_name in ("tech_analysis", "market_policy"):
                        progress_bar.progress(40, text=f"{node_name} 완료")
                    elif node_name == "policy_gate":
                        progress_bar.progress(50, text="정책 검증 완료")
                    elif node_name == "competitor_analysis":
                        progress_bar.progress(60, text="경쟁사 분석 완료")
                    elif node_name == "investment_decision":
                        progress_bar.progress(75, text="투자 판단 완료")
                    elif node_name == "evaluation_check":
                        progress_bar.progress(85, text="평가 검증 완료")
                    elif node_name == "report_writer":
                        progress_bar.progress(95, text="보고서 생성 완료")

                if final_state is None:
                    final_state = {}
                final_state = deep_merge(final_state, node_output)

    if show_progress:
        progress_bar.progress(100, text="평가 완료!")

    return final_state


def display_single_result(final_state: dict, startup_name: str):
    """단일 평가 결과 표시."""
    if final_state is None:
        st.error("평가 실행에 실패했습니다.")
        return

    cs = final_state.get("current_startup", {})
    flags = cs.get("pipeline_flags", {})

    if not flags.get("domain_check_passed", False):
        st.error(f"✗ **{startup_name}**은(는) Energy 도메인에 해당하지 않습니다.")
        domain_cls = cs.get("domain_classification", {})
        reason = domain_cls.get("reason", "N/A") if isinstance(domain_cls, dict) else "N/A"
        st.info(f"사유: {reason}")
        return

    if final_state.get("working", {}).get("policy_violation", False):
        st.error(f"✗ **{startup_name}**: 정책 위반으로 평가가 종료되었습니다.")
        st.info(f"사유: {final_state.get('working', {}).get('policy_violation_reason', 'N/A')}")
        return

    # Header metrics
    inv = cs.get("investment_decision", {})
    verdict = inv.get("verdict", "N/A")
    weighted_score = inv.get("weighted_score", 0)
    comp_analysis = cs.get("competition_analysis", {})
    comp_score = comp_analysis.get("competitiveness_score", 0) if isinstance(comp_analysis, dict) else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        color = "🟢" if verdict == "invest" else "🟡"
        st.metric("판정", f"{color} {verdict.upper()}")
    with col2:
        st.metric("가중합 점수", f"{weighted_score:.1f} / 100")
    with col3:
        st.metric("경쟁력 점수", f"{comp_score} / 10")
    with col4:
        report_path = final_state.get("outputs", {}).get("report_output_path", "")
        ext = os.path.splitext(report_path)[1] if report_path else ""
        st.metric("보고서", f"{'PDF' if ext == '.pdf' else 'Markdown'} 생성 완료")

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 점수표", "🏢 기업 프로필", "🔬 기술 분석",
        "📈 시장/정책", "⚔️ 경쟁사", "📄 보고서", "🔍 CRAG 로그",
    ])

    with tab1:
        st.subheader("9개 항목 점수표")
        criteria_scores = inv.get("criteria_scores", {})

        score_data = []
        for key, info in EVALUATION_CRITERIA.items():
            score_entry = criteria_scores.get(key, {})
            score_data.append({
                "항목": info["name"],
                "비중": f"{int(info['weight'] * 100)}%",
                "점수": score_entry.get("score", "N/A"),
                "근거": score_entry.get("justification", "N/A"),
            })

        st.table(score_data)
        st.metric("가중합 점수", f"{weighted_score:.1f}")
        st.info(inv.get("investment_memo", ""))

    with tab2:
        st.subheader("기업 프로필")
        profile = cs.get("company_profile", {})
        if profile:
            for k, v in profile.items():
                if isinstance(v, (list, dict)):
                    st.json(v)
                else:
                    st.markdown(f"**{k}**: {v}")

    with tab3:
        st.subheader("기술 분석")
        tech = cs.get("technology_analysis", {})
        if isinstance(tech, dict):
            if tech.get("parse_error"):
                st.markdown(tech.get("summary", ""))
            else:
                for k, v in tech.items():
                    st.markdown(f"**{k}**")
                    st.write(v)
        else:
            st.write(tech)

    with tab4:
        st.subheader("시장/정책 분석")
        market = cs.get("market_policy_analysis", {})
        if isinstance(market, dict):
            for k, v in market.items():
                st.markdown(f"**{k}**")
                st.write(v)
        else:
            st.write(market)

    with tab5:
        st.subheader("경쟁사 분석")
        competitor = cs.get("competition_analysis", {})
        if isinstance(competitor, dict):
            direct = competitor.get("direct_competitors", [])
            if direct and isinstance(direct, list):
                st.markdown("### 직접 경쟁사")
                st.table(direct)
            for k, v in competitor.items():
                if k != "direct_competitors":
                    st.markdown(f"**{k}**")
                    st.write(v)
        else:
            st.write(competitor)

    with tab6:
        st.subheader("투자 보고서")
        report_path = final_state.get("outputs", {}).get("report_output_path", "")

        if report_path and os.path.exists(report_path):
            if report_path.endswith(".pdf"):
                with open(report_path, "rb") as f:
                    st.download_button(
                        "📥 PDF 다운로드",
                        data=f.read(),
                        file_name=os.path.basename(report_path),
                        mime="application/pdf",
                    )
                md_path = report_path.replace(".pdf", ".md")
                if os.path.exists(md_path):
                    with open(md_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())
            elif report_path.endswith(".md"):
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    st.markdown(content)
                    st.download_button(
                        "📥 Markdown 다운로드",
                        data=content,
                        file_name=os.path.basename(report_path),
                    )

    with tab7:
        st.subheader("Corrective RAG 그레이딩 로그")
        rag_log = final_state.get("rag_grading_log", [])
        if rag_log:
            for entry in rag_log:
                st.text(entry)
        else:
            st.info("CRAG 로그 없음")

    # Log
    with st.expander("🔧 실행 로그"):
        for entry in final_state.get("log", []):
            st.text(entry)
        st.subheader("출처")
        for src in final_state.get("sources", []):
            st.text(src)


# ══════════════════════════════════════════════════════════════
# Single Mode
# ══════════════════════════════════════════════════════════════
if mode == "Single":
    startup_name = st.text_input(
        "스타트업명을 입력하세요",
        placeholder="예: 스탠다드에너지, 에이프릴, 바이오리즈 등",
    )

    run_button = st.button("🔍 투자 평가 시작", type="primary", disabled=not startup_name)

    if run_button and startup_name:
        retriever = init_rag()
        final_state = run_single_evaluation(startup_name, retriever)
        st.divider()
        display_single_result(final_state, startup_name)

# ══════════════════════════════════════════════════════════════
# Batch Mode
# ══════════════════════════════════════════════════════════════
elif mode == "Batch":
    st.subheader("배치 모드")
    st.caption("에너지 도메인 스타트업 10개를 자동으로 탐색하여 평가합니다.")

    batch_count = 10

    batch_button = st.button("🚀 배치 평가 시작", type="primary")

    if batch_button:
        retriever = init_rag()

        # ── 1. 스타트업 탐색 ──────────────────────────────────
        with st.spinner(f"에너지 도메인 스타트업 {batch_count}개 탐색 중..."):
            from app import _discover_with_descriptions, _batch_domain_check, _to_canonical, generate_batch_summary_report
            from config import BATCH_DOMAIN_REJECTION_THRESHOLD, EVALUATION_MAX_SCORES
            startup_names, startup_descs = _discover_with_descriptions(batch_count)

        if not startup_names:
            st.error("스타트업을 찾지 못했습니다.")
            st.stop()

        st.success(f"탐색된 스타트업: {', '.join(startup_names)}")

        # ── 2. 배치 도메인 필터 (LLM 1회, 설명 포함) ──────────
        with st.spinner("도메인 적합성 일괄 검증 중..."):
            domain_fit_names = _batch_domain_check(startup_names, startup_descs)
            rejected_names = [n for n in startup_names if n not in domain_fit_names]

        if rejected_names:
            st.warning(f"도메인 부적합: {', '.join(rejected_names)}")

        # ── 3. 부적합 비율 초과 시 재탐색 ─────────────────────
        if startup_names and len(rejected_names) / len(startup_names) > BATCH_DOMAIN_REJECTION_THRESHOLD:
            with st.spinner("도메인 적합 스타트업 재탐색 중..."):
                new_names, new_descs = _discover_with_descriptions(batch_count)
                new_fit = _batch_domain_check(new_names, new_descs)
                for name in new_fit:
                    if name not in domain_fit_names:
                        domain_fit_names.append(name)
                domain_fit_names = domain_fit_names[:batch_count]

        if not domain_fit_names:
            st.error("도메인 적합 스타트업이 없습니다.")
            st.stop()

        st.info(f"평가 대상: {', '.join(domain_fit_names)}")

        # ── 4. 배치 그래프 구축 + 개별 평가 ───────────────────
        from graph.batch_workflow import build_batch_graph
        batch_app = build_batch_graph(retriever=retriever)

        all_results = []
        for i, name in enumerate(domain_fit_names):
            st.subheader(f"[{i+1}/{len(domain_fit_names)}] {name}")

            initial_state = {
                "current_startup": {
                    "metadata": {"question": name, "status": "pending"},
                },
                "sources": [],
                "log": [],
                "rag_grading_log": [],
            }

            progress_bar = st.progress(0, text="파이프라인 시작...")
            final_state = None

            with st.spinner(f"{name} 투자 평가 진행 중..."):
                progress_map = {
                    "startup_search": (15, "스타트업 소싱 완료"),
                    "tech_analysis": (30, "기술 분석 완료"),
                    "market_policy": (35, "시장/정책 분석 완료"),
                    "batch_fan_in": (45, "분석 결과 수집 완료"),
                    "batch_competitor": (55, "경쟁사 분석 완료"),
                    "batch_input_validation": (65, "입력 검증 완료"),
                    "batch_investment_decision": (80, "투자 판단 완료"),
                    "batch_evaluation_check": (90, "평가 검증 완료"),
                    "batch_aggregation": (95, "집계 완료"),
                }
                for event in batch_app.stream(initial_state, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_name in progress_map:
                            pct, text = progress_map[node_name]
                            progress_bar.progress(pct, text=text)
                        if final_state is None:
                            final_state = {}
                        final_state = deep_merge(final_state, node_output)

            progress_bar.progress(100, text="평가 완료!")
            all_results.append(final_state)

        # ── 5. Canonical 변환 ─────────────────────────────────
        canonical_results = [
            _to_canonical(r, i + 1) for i, r in enumerate(all_results) if r
        ]

        st.divider()

        if not canonical_results:
            st.warning("유효한 평가 결과가 없습니다.")
            st.stop()

        # ── 6. 결과 표시 ─────────────────────────────────────
        tab_individual, tab_summary = st.tabs(["📋 개별 결과", "📊 요약 보고서"])

        with tab_individual:
            for fs, cr in zip(all_results, canonical_results):
                if fs is None:
                    continue
                cname = cr.get("company_name", "?")
                verdict = cr.get("verdict", "?")
                total = cr.get("total_score", 0)
                badge = "🟢 INVEST" if verdict == "invest" else "🔴 REJECT"

                with st.expander(f"📌 {cname} — {badge} ({total}/100)", expanded=False):
                    # 정책 위반 경고
                    if fs.get("working", {}).get("policy_violation", False):
                        st.warning(f"정책 위반: {fs.get('working', {}).get('policy_violation_reason', 'N/A')}")

                    # 메트릭
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("판정", f"{badge}")
                    with col2:
                        st.metric("총점", f"{total} / 100")
                    with col3:
                        cs = fs.get("current_startup", {})
                        comp = cs.get("competition_analysis", {})
                        if isinstance(comp, dict) and comp.get("analyzed", False):
                            st.metric("경쟁력", f"{comp.get('competitiveness_score', 0)}/10")
                        else:
                            st.metric("경쟁사 분석", "생략됨")

                    st.divider()

                    # 점수표 (score/max_score)
                    st.markdown("**9개 항목 점수표**")
                    inv = cs.get("investment_decision", {})
                    criteria_scores = inv.get("criteria_scores", {})
                    score_data = []
                    for key, info in EVALUATION_CRITERIA.items():
                        entry = criteria_scores.get(key, {})
                        ms = EVALUATION_MAX_SCORES.get(key, 0)
                        score_data.append({
                            "항목": info["name"],
                            "점수": f"{entry.get('score', 0)} / {ms}",
                            "근거": entry.get("reason", entry.get("justification", "N/A")),
                            "증거": entry.get("evidence", "N/A"),
                        })
                    st.table(score_data)
                    st.info(inv.get("investment_memo", ""))

                    # 상세 탭
                    t1, t2, t3, t4 = st.tabs(["🏢 프로필", "🔬 기술", "📈 시장/정책", "⚔️ 경쟁사"])
                    with t1:
                        profile = cs.get("company_profile", {})
                        if profile:
                            for k, v in profile.items():
                                if isinstance(v, (list, dict)):
                                    st.json(v)
                                else:
                                    st.markdown(f"**{k}**: {v}")
                    with t2:
                        tech = cs.get("technology_analysis", {})
                        if isinstance(tech, dict):
                            for k, v in tech.items():
                                st.markdown(f"**{k}**")
                                st.write(v)
                    with t3:
                        market = cs.get("market_policy_analysis", {})
                        if isinstance(market, dict):
                            for k, v in market.items():
                                st.markdown(f"**{k}**")
                                st.write(v)
                    with t4:
                        competitor = cs.get("competition_analysis", {})
                        if isinstance(competitor, dict):
                            if not competitor.get("analyzed", True):
                                st.warning(f"생략됨: {competitor.get('skip_reason', 'N/A')}")
                            else:
                                direct = competitor.get("direct_competitors", [])
                                if direct and isinstance(direct, list):
                                    st.table(direct)
                                for k, v in competitor.items():
                                    if k not in ("direct_competitors", "analyzed"):
                                        st.markdown(f"**{k}**")
                                        st.write(v)

                    with st.expander("🔧 실행 로그"):
                        for entry in fs.get("log", []):
                            st.text(entry)

        with tab_summary:
            st.subheader("종합 요약")

            # 요약 테이블
            summary_data = []
            for cr in canonical_results:
                summary_data.append({
                    "스타트업": cr.get("company_name", "?"),
                    "도메인": cr.get("domain_classification", "?"),
                    "핵심 기술": cr.get("core_technology", "?")[:50],
                    "총점": f"{cr.get('total_score', 0)} / 100",
                    "판정": cr.get("verdict", "?").upper(),
                })
            st.table(summary_data)

            # 요약 보고서 생성
            with st.spinner("A4 요약 보고서 생성 중..."):
                report_path = generate_batch_summary_report(canonical_results)

            if os.path.exists(report_path):
                if report_path.endswith(".pdf"):
                    with open(report_path, "rb") as f:
                        st.download_button(
                            "📥 요약 보고서 PDF 다운로드",
                            data=f.read(),
                            file_name=os.path.basename(report_path),
                            mime="application/pdf",
                        )
                    md_path = report_path.replace(".pdf", ".md")
                    if os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8") as f:
                            st.markdown(f.read())
                elif report_path.endswith(".md"):
                    with open(report_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        st.markdown(content)
                        st.download_button(
                            "📥 요약 보고서 다운로드",
                            data=content,
                            file_name=os.path.basename(report_path),
                        )
