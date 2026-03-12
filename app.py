import sys
import os
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time

from config import (
    DOMAIN, INVESTMENT_THRESHOLD, LLM_MODEL, OUTPUT_DIR,
    BATCH_DOMAIN_REJECTION_THRESHOLD, EVALUATION_MAX_SCORES,
    BATCH_MAX_CONCURRENCY, BATCH_CHUNK_SIZE,
    BATCH_TOTAL_TIMEOUT, BATCH_PER_STARTUP_TIMEOUT, BATCH_RESULTS_DIR,
    BATCH_FIXED_COUNT, SINGLE_RESULTS_DIR,
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
        "current_startup": {
            "metadata": {"question": startup_name, "status": "pending"},
        },
        "sources": [],
        "log": [],
        "rag_grading_log": [],
    }

    print("\n[실행] 투자 평가 파이프라인 시작...\n")
    final_state = app.invoke(initial_state)

    # 결과 출력
    print("\n" + "=" * 60)
    print("  평가 완료")
    print("=" * 60)

    cs = final_state.get("current_startup", {})
    flags = cs.get("pipeline_flags", {})

    if not flags.get("domain_check_passed", False):
        domain_cls = cs.get("domain_classification", {})
        reason = domain_cls.get("reason", "N/A") if isinstance(domain_cls, dict) else "N/A"
        print(f"  ✗ {startup_name}은(는) Energy 도메인에 해당하지 않습니다.")
        print(f"  사유: {reason}")
    elif final_state.get("working", {}).get("policy_violation", False):
        reason = final_state.get("working", {}).get("policy_violation_reason", "N/A")
        print(f"  ✗ {startup_name}: 정책 위반으로 평가 종료.")
        print(f"  사유: {reason}")
    else:
        inv = cs.get("investment_decision", {})
        verdict = inv.get("verdict", "N/A")
        score = inv.get("weighted_score", 0)
        print(f"  스타트업  : {startup_name}")
        print(f"  가중합 점수: {score:.1f} / 100")
        print(f"  판정      : {verdict.upper()}")
        report_path = final_state.get("outputs", {}).get("report_output_path", "N/A")
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
    """웹 검색으로 스타트업 탐색 (도메인 무관, 범용 검색)."""
    from tools.search import web_search
    from langchain_openai import ChatOpenAI
    from prompts.templates import BATCH_DISCOVER_PROMPT

    print(f"\n[배치 모드] 스타트업 {count}개 탐색 중...")

    search_results = web_search(
        "한국 유망 스타트업 투자 2024 2025",
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
    invest_results = [r for r in results if r.get("current_startup", {}).get("investment_decision", {}).get("verdict") == "invest"]
    all_hold = len(invest_results) == 0

    # 결과 요약 JSON
    summaries = []
    for r in results:
        cs = r.get("current_startup", {})
        profile = cs.get("company_profile", {})
        inv = cs.get("investment_decision", {})
        summaries.append({
            "company_name": profile.get("company_name", "Unknown"),
            "domain_classification": profile.get("domain_classification", ""),
            "core_technology": profile.get("core_technology", ""),
            "weighted_score": inv.get("weighted_score", 0),
            "verdict": inv.get("verdict", "N/A"),
            "competitiveness_score": cs.get("competition_analysis", {}).get("competitiveness_score", 0),
            "investment_memo": inv.get("investment_memo", ""),
            "criteria_scores": inv.get("criteria_scores", {}),
            "policy_violation": r.get("working", {}).get("policy_violation", False),
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
    os.makedirs(BATCH_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(BATCH_RESULTS_DIR, f"batch_comparison_report_{timestamp}.md")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[배치 모드] Markdown 저장: {md_path}")

    # PDF 변환
    pdf_path = os.path.join(BATCH_RESULTS_DIR, f"batch_comparison_report_{timestamp}.pdf")
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


def _discover_with_descriptions(count: int, general: bool = False) -> tuple[list[str], dict[str, str]]:
    """웹 검색으로 스타트업 탐색 + 한줄 설명 반환.

    count > 10 이면 다중 쿼리로 페이지네이션.
    general=True 이면 전체 도메인 대상.
    """
    from tools.search import web_search
    from langchain_openai import ChatOpenAI

    # 기본: 에너지 세부 도메인별 특화 쿼리
    # --general: 범용 도메인 쿼리 추가
    base_queries = [
        "한국 배터리 스타트업 투자 2024 2025",
        "한국 ESS 에너지저장 스타트업 투자",
        "한국 수소 연료전지 스타트업",
        "한국 태양광 풍력 재생에너지 스타트업",
        "한국 전력인프라 스마트그리드 스타트업",
        "한국 CCUS 탄소포집 에너지효율 스타트업",
    ]

    extra_queries = [
        "한국 유망 스타트업 투자 2024 2025",
        "한국 스타트업 시리즈A B 투자 유치",
        "한국 AI 딥테크 스타트업 투자",
        "한국 바이오 헬스케어 스타트업 투자 유망",
        "한국 핀테크 SaaS B2B 스타트업",
        "한국 모빌리티 로봇 자율주행 스타트업",
        "한국 환경 탄소 기후테크 스타트업",
        "한국 우주 방산 반도체 소재 스타트업",
    ]

    queries = base_queries + (extra_queries if general else [])

    label = "확장 탐색" if general else "기본 탐색"
    print(f"\n[배치 모드] {label} 스타트업 {count}개 탐색 중...")

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    all_names: list[str] = []
    all_descs: dict[str, str] = {}
    names_per_round = max(count // len(queries) + 2, 8)

    for qi, query in enumerate(queries):
        if len(all_names) >= count:
            break

        search_results = web_search(query, max_results=10)
        needed = min(names_per_round, count - len(all_names))
        exclude_json = json.dumps(all_names, ensure_ascii=False) if all_names else "없음"

        prompt = f"""아래 웹 검색 결과에서 투자 검토 대상이 될 수 있는 **한국 에너지 도메인 스타트업 {needed}개**를 선별하세요.
에너지 도메인: 배터리, ESS, 수소, 태양광, 풍력, 전력 인프라, 에너지 효율, 스마트그리드, CCUS 등.
각 스타트업의 이름과 핵심 기술/사업을 한 줄로 설명하세요. 에너지와 무관한 스타트업은 제외하세요.

## 이미 선별됨 (제외)
{exclude_json}

## 웹 검색 결과
{search_results}

중복 없이 {needed}개를 아래 JSON으로만 반환:
[{{"name": "회사명", "desc": "핵심 기술/사업 한줄 설명"}}]"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(content)
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict):
                        name = str(d.get("name", "")).strip()
                        desc = str(d.get("desc", "")).strip()
                    else:
                        name = str(d).strip()
                        desc = ""
                    if name and name not in all_names:
                        all_names.append(name)
                        all_descs[name] = desc
        except json.JSONDecodeError:
            pass

        print(f"  [{qi+1}/{min(len(queries), count//names_per_round+1)}] → 누적 {len(all_names)}개")

    all_names = all_names[:count]
    print(f"\n[배치 모드] 총 {len(all_names)}개 스타트업 탐색 완료")
    for n in all_names:
        print(f"  - {n}: {all_descs.get(n, '')}")

    return all_names, {n: all_descs.get(n, "") for n in all_names}


def _batch_domain_check(names: list[str], descriptions: dict[str, str] | None = None) -> list[str]:
    """배치 도메인 필터: 1회 LLM 호출로 전체 필터링 (설명 포함)."""
    from langchain_openai import ChatOpenAI

    if not names:
        return []

    # 설명이 있으면 포함, 없으면 이름만
    if descriptions:
        entries = "\n".join(f"- {n}: {descriptions.get(n, '정보 없음')}" for n in names)
    else:
        entries = "\n".join(f"- {n}" for n in names)

    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    prompt = f"""아래 스타트업 목록에서 **Energy 도메인**에 해당하는 것만 골라주세요.
Energy 도메인: 배터리, ESS, 수소, 태양광, 풍력, 전력 인프라, 에너지 효율, 스마트그리드, 에너지전환, CCUS 등.

스타트업 목록:
{entries}

Energy 도메인에 해당하는 스타트업 이름만 JSON 배열로 반환하세요. JSON만:"""

    response = llm.invoke(prompt)
    content = response.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        filtered = json.loads(content)
        if isinstance(filtered, list):
            return [str(n).strip() for n in filtered if str(n).strip() in names]
    except json.JSONDecodeError:
        pass

    # 파싱 실패 시 전체 통과 (이미 Energy 검색에서 나온 결과)
    print("[배치 모드] 도메인 필터 파싱 실패. 전체 통과 처리.")
    return names


def _to_canonical(state: dict, batch_id: int) -> dict:
    """배치 결과를 canonical schema로 변환.

    graph 내 batch_aggregation_node가 outputs.aggregation_result를 생성한 경우
    그것을 직접 사용. 없으면 nested state에서 추출.
    """
    agg = state.get("outputs", {}).get("aggregation_result", {})
    if agg:
        canonical = dict(agg)
        canonical["batch_id"] = batch_id
        return canonical

    # Fallback: nested state에서 추출
    cs = state.get("current_startup", {})
    profile = cs.get("company_profile", {})
    inv = cs.get("investment_decision", {})
    comp = cs.get("competition_analysis", {})

    return {
        "batch_id": batch_id,
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


def _save_result(canonical: dict, session_dir: str) -> str:
    """개별 스타트업 평가 결과를 JSON으로 즉시 저장."""
    os.makedirs(session_dir, exist_ok=True)
    bid = canonical["batch_id"]
    name = canonical["company_name"].replace("/", "_").replace(" ", "_")
    filename = f"{bid:03d}_{name}.json"
    filepath = os.path.join(session_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(canonical, f, ensure_ascii=False, indent=2)

    return filepath


def _load_saved_results(session_dir: str) -> list[dict]:
    """세션 디렉토리에서 저장된 평가 결과 전부 로드."""
    if not os.path.exists(session_dir):
        return []

    results = []
    for fname in sorted(os.listdir(session_dir)):
        if fname.endswith(".json") and fname != "session_meta.json":
            fpath = os.path.join(session_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                results.append(json.load(f))

    return results


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
    os.makedirs(BATCH_RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(BATCH_RESULTS_DIR, f"batch_summary_report_{timestamp}.md")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[배치 모드] Markdown 저장: {md_path}")

    # PDF 변환
    pdf_path = os.path.join(BATCH_RESULTS_DIR, f"batch_summary_report_{timestamp}.pdf")
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


def main_batch(general: bool = False):
    """배치 모드: 10개 스타트업 자동 탐색 → 도메인 필터 → 청크 병렬 평가 → 즉시 저장 → 요약 보고서."""
    from graph.batch_workflow import build_batch_graph

    count = BATCH_FIXED_COUNT
    label = "전체 도메인" if general else "에너지 도메인"
    print("=" * 60)
    print(f"  AI 스타트업 투자 평가 에이전트 — 배치 모드 ({count}개, {label})")
    print("=" * 60)

    t_start = time.time()

    # ── 세션 디렉토리 생성 ────────────────────────────────────────
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(BATCH_RESULTS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # ── 1. 스타트업 탐색 (이름 + 설명) ─────────────────────────
    startup_names, startup_descs = _discover_with_descriptions(count, general=general)
    if not startup_names:
        print("[배치 모드] 스타트업을 찾지 못했습니다. 종료합니다.")
        return

    rejected_names = []

    if general:
        domain_fit_names = startup_names
        print(f"\n[배치 모드] 전체 도메인 모드: 필터 생략, {len(domain_fit_names)}개 전부 평가")
    else:
        # ── 2. 배치 도메인 필터 (LLM 1회, 설명 포함) ────────────
        print("\n[배치 모드] 도메인 적합성 일괄 검증 중...")
        domain_fit_names = _batch_domain_check(startup_names, startup_descs)
        rejected_names = [n for n in startup_names if n not in domain_fit_names]

        if domain_fit_names:
            print(f"  ✓ 적합: {', '.join(domain_fit_names)}")
        if rejected_names:
            print(f"  ✗ 부적합: {', '.join(rejected_names)}")

        # ── 도메인 부적합 스타트업 → reject JSON 즉시 저장 ───────
        for ri, rname in enumerate(rejected_names):
            desc = startup_descs.get(rname, "")
            canonical = {
                "batch_id": ri + 1,
                "company_name": rname,
                "domain_classification": desc,
                "core_technology": desc,
                "total_score": 0,
                "verdict": "reject",
                "criteria_scores": {},
                "investment_memo": f"Energy 도메인 부적합으로 기각. 사업 내용: {desc}" if desc else "Energy 도메인 부적합으로 기각.",
                "policy_violation": False,
                "policy_violation_reason": "",
                "competitor_analyzed": False,
                "competitiveness_score": None,
                "reject_reason": "domain_mismatch",
            }
            _save_result(canonical, session_dir)

        if rejected_names:
            print(f"  → 도메인 부적합 {len(rejected_names)}개 기각 저장 완료")

        # ── 3. 부적합 비율 초과 시 재탐색 (max 1) ───────────────
        if startup_names and len(rejected_names) / len(startup_names) > BATCH_DOMAIN_REJECTION_THRESHOLD:
            print(f"\n[배치 모드] 도메인 부적합 비율 초과. 재탐색 수행.")
            new_names, new_descs = _discover_with_descriptions(count)
            new_fit = _batch_domain_check(new_names, new_descs)
            for name in new_fit:
                if name not in domain_fit_names:
                    domain_fit_names.append(name)
            domain_fit_names = domain_fit_names[:count]

    print(f"\n[배치 모드] 최종 평가 대상 ({len(domain_fit_names)}개): {', '.join(domain_fit_names) if domain_fit_names else '없음'}")
    print(f"  도메인 기각: {len(rejected_names)}개")

    # ── 세션 메타 저장 ────────────────────────────────────────────
    meta = {
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "count": count,
        "general": general,
        "all_startups": startup_names,
        "domain_fit": domain_fit_names,
        "domain_rejected": rejected_names,
    }
    with open(os.path.join(session_dir, "session_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # ── 4. 도메인 적합 스타트업이 있으면 평가 실행 ────────────────
    timed_out = False
    eval_count = 0

    if domain_fit_names:
        print("\n[설정] RAG 벡터스토어 구축 중...")
        vectorstore = build_vectorstore()
        retriever = get_retriever(vectorstore)

        print("[설정] 배치 에이전트 그래프 구축 중...")
        batch_app = build_batch_graph(retriever=retriever)

        # ── 5. 청크 단위 병렬 평가 + 즉시 저장 ───────────────────
        chunk_size = BATCH_CHUNK_SIZE
        concurrency = min(chunk_size, BATCH_MAX_CONCURRENCY)
        total_eval = len(domain_fit_names)
        batch_id_offset = len(rejected_names)  # 도메인 reject 이후 번호 이어감

        print(f"\n[배치 모드] {total_eval}개 평가 시작 (청크 {chunk_size}개, 동시 {concurrency}개, 타임아웃 {BATCH_TOTAL_TIMEOUT}초)")

        t_eval = time.time()

        for chunk_start in range(0, total_eval, chunk_size):
            elapsed = time.time() - t_start
            if elapsed >= BATCH_TOTAL_TIMEOUT:
                remaining = total_eval - chunk_start
                print(f"\n[배치 모드] ⏱ 전체 타임아웃 ({BATCH_TOTAL_TIMEOUT}초) 도달. 나머지 {remaining}개 생략.")
                timed_out = True
                break

            chunk_names = domain_fit_names[chunk_start:chunk_start + chunk_size]
            chunk_num = chunk_start // chunk_size + 1
            total_chunks = (total_eval + chunk_size - 1) // chunk_size
            print(f"\n[청크 {chunk_num}/{total_chunks}] {len(chunk_names)}개 평가 중... ({', '.join(chunk_names)})")

            inputs = [
                {
                    "current_startup": {
                        "metadata": {"question": name, "status": "pending"},
                    },
                    "sources": [],
                    "log": [],
                    "rag_grading_log": [],
                }
                for name in chunk_names
            ]

            raw_results = batch_app.batch(
                inputs,
                config={"max_concurrency": concurrency},
                return_exceptions=True,
            )

            for i, result in enumerate(raw_results):
                name = chunk_names[i]
                bid = batch_id_offset + i + 1

                if isinstance(result, Exception):
                    print(f"  ✗ {name}: 평가 실패 ({result})")
                    canonical = _to_canonical(
                        {
                            "current_startup": {
                                "company_profile": {"company_name": name},
                                "investment_decision": {
                                    "verdict": "reject",
                                    "weighted_score": 0,
                                    "criteria_scores": {},
                                },
                            },
                        },
                        bid,
                    )
                else:
                    agg = result.get("outputs", {}).get("aggregation_result", {})
                    verdict = agg.get("verdict", "N/A")
                    total_score = agg.get("total_score", 0)
                    print(f"  ✓ {name}: {verdict.upper()} ({total_score}/100)")
                    canonical = _to_canonical(result, bid)

                fpath = _save_result(canonical, session_dir)
                print(f"    → 저장: {os.path.basename(fpath)}")

            batch_id_offset += len(chunk_names)
            eval_count += len(chunk_names)

        t_eval_done = time.time()
        print(f"\n[배치 모드] 평가 완료 ({t_eval_done - t_eval:.1f}초)")
        if timed_out:
            print(f"  ⚠ 타임아웃으로 {eval_count}/{total_eval}개만 평가됨")
    else:
        print("\n[배치 모드] 도메인 적합 스타트업 0개. 전원 기각 보고서를 생성합니다.")

    # ── 6. 저장된 JSON 로드 + 보고서 생성 ─────────────────────────
    canonical_results = _load_saved_results(session_dir)

    if not canonical_results:
        print("\n[배치 모드] 평가 결과가 없습니다. 보고서 생성을 건너뜁니다.")
        return

    report_path = generate_batch_summary_report(canonical_results)

    # ── 결과 요약 출력 ───────────────────────────────────────────
    t_end = time.time()
    total_all = len(startup_names)
    invest_count = sum(1 for c in canonical_results if c["verdict"] == "invest")
    reject_count = sum(1 for c in canonical_results if c["verdict"] == "reject")
    domain_reject_count = sum(1 for c in canonical_results if c.get("reject_reason") == "domain_mismatch")

    print("\n" + "=" * 60)
    print("  배치 평가 완료")
    print("=" * 60)
    print(f"  세션 ID    : {session_id}")
    print(f"  결과 저장  : {session_dir}")
    print(f"  총 소요시간: {t_end - t_start:.1f}초")
    print(f"  탐색       : {total_all}개")
    print(f"  도메인 적합: {len(domain_fit_names)}개 → 상세 평가")
    print(f"  도메인 기각: {domain_reject_count}개")
    print(f"  invest     : {invest_count}개")
    print(f"  reject     : {reject_count}개 (도메인 기각 {domain_reject_count}개 포함)")
    print(f"  ── 투자 추천 ──")
    for c in canonical_results:
        if c["verdict"] == "invest":
            print(f"    ★ {c['company_name']}: INVEST ({c['total_score']}/100)")
    print(f"  ── 기각 ──")
    for c in canonical_results:
        if c["verdict"] == "reject":
            reason = c.get("reject_reason", "")
            memo = c.get("investment_memo", "")
            if reason == "domain_mismatch":
                print(f"    ✗ {c['company_name']}: REJECT (도메인 부적합) — {c.get('core_technology', '')[:40]}")
            else:
                print(f"    ✗ {c['company_name']}: REJECT ({c['total_score']}/100) — {memo[:40]}")
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
        action="store_true",
        help="배치 모드: 10개 스타트업 자동 탐색 및 평가",
    )
    parser.add_argument(
        "--general",
        action="store_true",
        help="전체 도메인 스타트업 탐색 (에너지 제한 해제)",
    )

    args = parser.parse_args()

    if args.batch:
        main_batch(general=args.general)
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
