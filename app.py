import sys
import os
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DOMAIN, INVESTMENT_THRESHOLD, LLM_MODEL, OUTPUT_DIR,
    BATCH_DOMAIN_REJECTION_THRESHOLD, EVALUATION_MAX_SCORES,
)
from rag.retriever import build_vectorstore, get_retriever
from graph.workflow import build_graph


def main_single(startup_name: str, retriever=None, app=None) -> dict:
    """단일 스타트업 투자 평가."""
    print("=" * 60)
    print("  AI 스타트업 투자 평가 에이전트")
    print("=" * 60)
    print(f"  대상 스타트업 : {startup_name}")
    print(f"  도메인        : {DOMAIN}")
    print(f"  투자 기준점수 : {INVESTMENT_THRESHOLD}")
    print("=" * 60)

    # 공유 리소스가 없으면 개별 생성
    if retriever is None:
        print("\n[설정] RAG 벡터스토어 구축 중...")
        vectorstore = build_vectorstore()
        retriever = get_retriever(vectorstore)

    if app is None:
        print("[설정] 에이전트 그래프 구축 중...")
        app = build_graph(retriever=retriever)

    initial_state = {
        "question": startup_name,
        "sources": [],
        "log": [],
        "rag_grading_log": [],
        "status": "pending",
    }

    print("\n[실행] 투자 평가 파이프라인 시작...\n")
    final_state = app.invoke(initial_state)

    # 결과 출력
    print("\n" + "=" * 60)
    print("  평가 완료")
    print("=" * 60)

    if not final_state.get("domain_fit", False):
        print(f"  ✗ {startup_name}은(는) Energy 도메인에 해당하지 않습니다.")
        print(f"  사유: {final_state.get('domain_fit_reason', 'N/A')}")
    elif final_state.get("policy_violation", False):
        print(f"  ✗ {startup_name}: 정책 위반으로 평가 종료.")
        print(f"  사유: {final_state.get('policy_violation_reason', 'N/A')}")
    else:
        verdict = final_state.get("verdict", "N/A")
        score = final_state.get("weighted_score", 0)
        print(f"  스타트업  : {startup_name}")
        print(f"  가중합 점수: {score:.1f} / 100")
        print(f"  판정      : {verdict.upper()}")
        report_path = final_state.get("investment_report", "N/A")
        print(f"  보고서    : {report_path}")

    # CRAG 로그 출력
    rag_log = final_state.get("rag_grading_log", [])
    if rag_log:
        print("\n  [Corrective RAG 로그]")
        for entry in rag_log:
            print(f"    {entry}")

    print("=" * 60)

    return final_state


def discover_startups(count: int) -> list[str]:
    """웹 검색으로 에너지 도메인 스타트업 탐색."""
    from tools.search import web_search
    from langchain_openai import ChatOpenAI
    from prompts.templates import BATCH_DISCOVER_PROMPT

    print(f"\n[배치 모드] 에너지 도메인 스타트업 {count}개 탐색 중...")

    search_results = web_search(
        "한국 에너지 스타트업 배터리 ESS 수소 태양광 투자 유망 2024 2025",
        max_results=10,
    )

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = BATCH_DISCOVER_PROMPT.format(
        count=count,
        search_results=search_results,
    )

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        names = json.loads(content)
        if isinstance(names, list):
            names = [str(n).strip() for n in names[:count]]
            print(f"[배치 모드] 탐색된 스타트업: {', '.join(names)}")
            return names
    except json.JSONDecodeError:
        pass

    print("[배치 모드] 스타트업 탐색 실패. 기본값 사용.")
    return []


def generate_comparison_report(results: list[dict]) -> str:
    """배치 결과 종합 비교 보고서 생성."""
    import markdown

    from langchain_openai import ChatOpenAI
    from prompts.templates import (
        BATCH_COMPARISON_REPORT_PROMPT,
        BATCH_HOLD_REPORT_PROMPT,
    )

    count = len(results)
    invest_results = [r for r in results if r.get("verdict") == "invest"]
    all_hold = len(invest_results) == 0

    # 결과 요약 JSON
    summaries = []
    for r in results:
        summaries.append({
            "company_name": r.get("startup_profile", {}).get("company_name", "Unknown"),
            "domain_classification": r.get("startup_profile", {}).get("domain_classification", ""),
            "core_technology": r.get("startup_profile", {}).get("core_technology", ""),
            "weighted_score": r.get("weighted_score", 0),
            "verdict": r.get("verdict", "N/A"),
            "competitiveness_score": r.get("competitiveness_score", 0),
            "investment_memo": r.get("investment_memo", ""),
            "criteria_scores": r.get("criteria_scores", {}),
            "policy_violation": r.get("policy_violation", False),
        })

    results_json = json.dumps(summaries, ensure_ascii=False, indent=2)
    names = [s["company_name"] for s in summaries]
    header_row = " | ".join(names)
    separator_row = " | ".join(["------"] * len(names))

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)

    if all_hold:
        prompt = BATCH_HOLD_REPORT_PROMPT.format(
            count=count,
            results_json=results_json,
        )
    else:
        prompt = BATCH_COMPARISON_REPORT_PROMPT.format(
            count=count,
            results_json=results_json,
            header_row=header_row,
            separator_row=separator_row,
        )

    print(f"\n[배치 모드] 종합 비교 보고서 생성 중...")
    response = llm.invoke(prompt)
    report_md = response.content.strip()

    # 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(OUTPUT_DIR, f"batch_comparison_report_{timestamp}.md")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[배치 모드] Markdown 저장: {md_path}")

    # PDF 변환
    pdf_path = os.path.join(OUTPUT_DIR, f"batch_comparison_report_{timestamp}.pdf")
    try:
        if not os.environ.get("DYLD_FALLBACK_LIBRARY_PATH"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib"
        from weasyprint import HTML

        html_content = markdown.markdown(
            report_md, extensions=["tables", "fenced_code"]
        )
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            margin: 40px;
            line-height: 1.6;
            font-size: 11pt;
            color: #1a202c;
        }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 8px; font-size: 20pt; margin-top: 30px; }}
        h2 {{ color: #2d3748; font-size: 15pt; margin-top: 24px; }}
        h3 {{ color: #4a5568; font-size: 13pt; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #cbd5e0; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #edf2f7; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f7fafc; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        HTML(string=styled_html).write_pdf(pdf_path)
        print(f"[배치 모드] PDF 저장: {pdf_path}")
    except Exception as e:
        print(f"[배치 모드] PDF 변환 실패: {e}")
        pdf_path = md_path

    return pdf_path


def _quick_domain_check(name: str) -> bool:
    """Quick domain pre-filter: 웹검색 + domain_check_node."""
    from tools.search import web_search
    from agents.domain_check import domain_check_node

    search_results = web_search(f"{name} 스타트업 에너지 기술", max_results=3)
    profile = {
        "company_name": name,
        "description": str(search_results)[:800] if search_results else name,
        "core_technology": "",
        "product_service": "",
    }
    result = domain_check_node({"startup_profile": profile, "log": []})
    return result.get("domain_fit", False)


def _to_canonical(state: dict, batch_id: int) -> dict:
    """배치 결과를 canonical schema로 변환."""
    profile = state.get("startup_profile", {})
    criteria = state.get("criteria_scores", {})
    comp = state.get("competitor_analysis", {})

    return {
        "batch_id": batch_id,
        "company_name": profile.get("company_name", "Unknown"),
        "domain_classification": profile.get("domain_classification", ""),
        "core_technology": profile.get("core_technology", ""),
        "total_score": int(state.get("weighted_score", 0)),
        "verdict": state.get("verdict", "reject"),
        "criteria_scores": criteria,
        "investment_memo": state.get("investment_memo", ""),
        "policy_violation": state.get("policy_violation", False),
        "policy_violation_reason": state.get("policy_violation_reason", ""),
        "competitor_analyzed": comp.get("analyzed", False) if isinstance(comp, dict) else False,
        "competitiveness_score": state.get("competitiveness_score"),
    }


def generate_batch_summary_report(canonical_results: list[dict]) -> str:
    """배치 결과 A4 1장 요약 보고서 생성."""
    import markdown
    from langchain_openai import ChatOpenAI
    from prompts.batch_templates import BATCH_SUMMARY_REPORT_PROMPT

    count = len(canonical_results)
    invest_results = [r for r in canonical_results if r.get("verdict") == "invest"]
    reject_results = [r for r in canonical_results if r.get("verdict") == "reject"]

    results_json = json.dumps(canonical_results, ensure_ascii=False, indent=2)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)
    prompt = BATCH_SUMMARY_REPORT_PROMPT.format(
        count=count,
        results_json=results_json,
        date=datetime.now().strftime("%Y-%m-%d"),
        invest_count=len(invest_results),
        reject_count=len(reject_results),
    )

    print(f"\n[배치 모드] A4 요약 보고서 생성 중...")
    response = llm.invoke(prompt)
    report_md = response.content.strip()

    # 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(OUTPUT_DIR, f"batch_summary_report_{timestamp}.md")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[배치 모드] Markdown 저장: {md_path}")

    # PDF 변환
    pdf_path = os.path.join(OUTPUT_DIR, f"batch_summary_report_{timestamp}.pdf")
    try:
        if not os.environ.get("DYLD_FALLBACK_LIBRARY_PATH"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib"
        from weasyprint import HTML

        html_content = markdown.markdown(
            report_md, extensions=["tables", "fenced_code"]
        )
        styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            margin: 40px;
            line-height: 1.6;
            font-size: 11pt;
            color: #1a202c;
        }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 8px; font-size: 20pt; margin-top: 30px; }}
        h2 {{ color: #2d3748; font-size: 15pt; margin-top: 24px; }}
        h3 {{ color: #4a5568; font-size: 13pt; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #cbd5e0; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #edf2f7; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f7fafc; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        HTML(string=styled_html).write_pdf(pdf_path)
        print(f"[배치 모드] PDF 저장: {pdf_path}")
    except Exception as e:
        print(f"[배치 모드] PDF 변환 실패: {e}")
        pdf_path = md_path

    return pdf_path


def main_batch(count: int):
    """배치 모드: N개 스타트업 자동 탐색 → 도메인 필터 → 배치 그래프 평가 → 요약 보고서."""
    from graph.batch_workflow import build_batch_graph

    print("=" * 60)
    print(f"  AI 스타트업 투자 평가 에이전트 — 배치 모드 ({count}개)")
    print("=" * 60)

    # ── 1. 스타트업 탐색 ─────────────────────────────────────────
    startup_names = discover_startups(count)
    if not startup_names:
        print("[배치 모드] 스타트업을 찾지 못했습니다. 종료합니다.")
        return

    # ── 2. 도메인 사전 필터 ──────────────────────────────────────
    print("\n[배치 모드] 도메인 적합성 사전 검증 중...")
    domain_fit_names: list[str] = []
    rejected_names: list[str] = []
    for name in startup_names:
        if _quick_domain_check(name):
            domain_fit_names.append(name)
            print(f"  ✓ {name}: Energy 도메인 적합")
        else:
            rejected_names.append(name)
            print(f"  ✗ {name}: Energy 도메인 부적합")

    # ── 3. 부적합 비율 초과 시 쿼리 재작성 + 재탐색 (max 1) ────
    if startup_names and len(rejected_names) / len(startup_names) > BATCH_DOMAIN_REJECTION_THRESHOLD:
        print(f"\n[배치 모드] 도메인 부적합 비율 초과 ({len(rejected_names)}/{len(startup_names)}). 재탐색 수행.")
        new_names = discover_startups(count)
        for name in new_names:
            if name not in domain_fit_names and name not in rejected_names:
                if _quick_domain_check(name):
                    domain_fit_names.append(name)
                    print(f"  ✓ (재탐색) {name}: Energy 도메인 적합")
        domain_fit_names = domain_fit_names[:count]

    if not domain_fit_names:
        print("\n[배치 모드] 도메인 적합 스타트업이 없습니다. 종료합니다.")
        return

    print(f"\n[배치 모드] 최종 평가 대상: {', '.join(domain_fit_names)}")

    # ── 4. 공유 리소스 구축 + 배치 그래프 ────────────────────────
    print("\n[설정] RAG 벡터스토어 구축 중...")
    vectorstore = build_vectorstore()
    retriever = get_retriever(vectorstore)

    print("[설정] 배치 에이전트 그래프 구축 중...")
    batch_app = build_batch_graph(retriever=retriever)

    # ── 5. 개별 평가 (배치 그래프) ───────────────────────────────
    results = []
    for i, name in enumerate(domain_fit_names, 1):
        print(f"\n{'#' * 60}")
        print(f"  [{i}/{len(domain_fit_names)}] {name} 배치 평가 시작")
        print(f"{'#' * 60}")

        initial_state = {
            "question": name,
            "sources": [],
            "log": [],
            "rag_grading_log": [],
            "status": "pending",
        }

        final_state = batch_app.invoke(initial_state)
        results.append(final_state)

        # 간이 결과 출력
        verdict = final_state.get("verdict", "N/A")
        total = int(final_state.get("weighted_score", 0))
        print(f"\n  → {name}: {verdict.upper()} ({total}/100)")

    # ── 6. Canonical 변환 + 집계 ─────────────────────────────────
    canonical_results = [_to_canonical(r, i + 1) for i, r in enumerate(results)]

    # ── 7. A4 1장 요약 보고서 생성 ───────────────────────────────
    report_path = generate_batch_summary_report(canonical_results)

    # ── 결과 요약 출력 ───────────────────────────────────────────
    invest_count = sum(1 for c in canonical_results if c["verdict"] == "invest")
    reject_count = sum(1 for c in canonical_results if c["verdict"] == "reject")

    print("\n" + "=" * 60)
    print("  배치 평가 완료")
    print("=" * 60)
    print(f"  평가 대상  : {len(domain_fit_names)}개")
    print(f"  invest     : {invest_count}개")
    print(f"  reject     : {reject_count}개")
    for c in canonical_results:
        print(f"    - {c['company_name']}: {c['verdict'].upper()} ({c['total_score']}/100)")
    print(f"  요약 보고서: {report_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="AI 스타트업 투자 평가 에이전트",
    )
    parser.add_argument(
        "startup_name",
        nargs="?",
        help="평가할 스타트업명 (single mode)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        metavar="N",
        help="배치 모드: N개 스타트업 자동 탐색 및 평가",
    )

    args = parser.parse_args()

    if args.batch:
        main_batch(args.batch)
    elif args.startup_name:
        main_single(args.startup_name)
    else:
        name = input("투자 평가할 스타트업명을 입력하세요: ").strip()
        if not name:
            print("스타트업명을 입력해주세요.")
            return
        main_single(name)


if __name__ == "__main__":
    main()
