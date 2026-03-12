"""배치 평가 결과 + CRAG 로그 분석 → 증빙자료(차트+리포트) 생성.

생성 항목:
  1. 배치 점수 분포 히스토그램
  2. 9개 항목별 레이더 차트 (invest vs reject 평균)
  3. 항목별 점수 박스플롯
  4. CRAG 로그 분석 (검색 통과율, fallback 비율)
  5. 종합 분석 리포트 (Markdown)

사용법:
  .venv/bin/python evaluation/generate_evidence.py [batch_session_dir]
  예: .venv/bin/python evaluation/generate_evidence.py outputs/batch_results/20260312_201127
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

from config import EVALUATION_CRITERIA, EVALUATION_MAX_SCORES, INVESTMENT_THRESHOLD, RAGAS_RESULTS_DIR

# 한글 폰트 설정
font_candidates = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]
for fp in font_candidates:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
        prop = fm.FontProperties(fname=fp)
        plt.rcParams["font.family"] = prop.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


def load_batch_results(session_dir: str) -> list[dict]:
    """배치 세션 디렉토리에서 개별 결과 JSON 로드."""
    results = []
    for f in sorted(os.listdir(session_dir)):
        if f.endswith(".json") and f != "session_meta.json":
            with open(os.path.join(session_dir, f), encoding="utf-8") as fh:
                data = json.load(fh)
                data["_filename"] = f
                results.append(data)
    return results


def find_latest_batch_session() -> str:
    """가장 최근 배치 세션 디렉토리 반환."""
    from config import BATCH_RESULTS_DIR
    batch_dir = BATCH_RESULTS_DIR
    if not os.path.exists(batch_dir):
        print(f"ERROR: {batch_dir} 디렉토리가 없습니다.")
        sys.exit(1)
    sessions = sorted(os.listdir(batch_dir), reverse=True)
    if not sessions:
        print("ERROR: 배치 결과가 없습니다.")
        sys.exit(1)
    return os.path.join(batch_dir, sessions[0])


# ── 1. 점수 분포 히스토그램 ──────────────────────────────────────
def plot_score_distribution(results: list[dict], output_dir: str):
    """배치 점수 분포 히스토그램."""
    scores = [r.get("total_score", 0) for r in results]
    names = [r.get("startup_name") or r.get("company_name", "?") for r in results]
    verdicts = [r.get("verdict", "reject") for r in results]

    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#2ecc71" if v == "invest" else "#e74c3c" for v in verdicts]

    # 점수순 정렬
    sorted_data = sorted(zip(scores, names, colors), reverse=True)
    scores_s, names_s, colors_s = zip(*sorted_data) if sorted_data else ([], [], [])

    bars = ax.barh(range(len(names_s)), scores_s, color=colors_s, edgecolor="white", height=0.7)

    ax.set_yticks(range(len(names_s)))
    ax.set_yticklabels(names_s, fontsize=10)
    ax.set_xlabel("총점 (100점 만점)", fontsize=12)
    ax.set_title("배치 투자 평가 — 스타트업별 총점 분포", fontsize=14, fontweight="bold")
    ax.axvline(x=INVESTMENT_THRESHOLD, color="#3498db", linestyle="--", linewidth=2, label=f"Threshold ({INVESTMENT_THRESHOLD}점)")
    ax.legend(fontsize=11)
    ax.invert_yaxis()

    # 점수 라벨
    for bar, score in zip(bars, scores_s):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{score}", va="center", fontsize=10, fontweight="bold")

    ax.set_xlim(0, 105)
    plt.tight_layout()
    path = os.path.join(output_dir, "score_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


# ── 2. 레이더 차트 ──────────────────────────────────────────────
def plot_radar_chart(results: list[dict], output_dir: str):
    """invest vs reject 평균 레이더 차트."""
    criteria_keys = list(EVALUATION_CRITERIA.keys())
    criteria_names = [EVALUATION_CRITERIA[k]["name"] for k in criteria_keys]
    max_scores = [EVALUATION_MAX_SCORES[k] for k in criteria_keys]

    invest_scores = {k: [] for k in criteria_keys}
    reject_scores = {k: [] for k in criteria_keys}

    for r in results:
        cs = r.get("criteria_scores", {})
        verdict = r.get("verdict", "reject")
        total = r.get("total_score", 0)
        # 도메인 부적합(0점) 제외
        if total == 0:
            continue
        for k in criteria_keys:
            score = 0
            if isinstance(cs.get(k), dict):
                score = cs[k].get("score", 0)
            elif isinstance(cs.get(k), (int, float)):
                score = cs[k]
            # 정규화 (0~1)
            normalized = score / max_scores[criteria_keys.index(k)] if max_scores[criteria_keys.index(k)] > 0 else 0
            if verdict == "invest":
                invest_scores[k].append(normalized)
            else:
                reject_scores[k].append(normalized)

    inv_avg = [np.mean(invest_scores[k]) if invest_scores[k] else 0 for k in criteria_keys]
    rej_avg = [np.mean(reject_scores[k]) if reject_scores[k] else 0 for k in criteria_keys]

    N = len(criteria_keys)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    inv_avg += inv_avg[:1]
    rej_avg += rej_avg[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(criteria_names, fontsize=9)

    ax.plot(angles, inv_avg, "o-", linewidth=2.5, label="Invest 평균", color="#2ecc71")
    ax.fill(angles, inv_avg, alpha=0.15, color="#2ecc71")
    ax.plot(angles, rej_avg, "o-", linewidth=2.5, label="Reject 평균", color="#e74c3c")
    ax.fill(angles, rej_avg, alpha=0.15, color="#e74c3c")

    ax.set_ylim(0, 1)
    ax.set_title("항목별 Invest vs Reject 평균 비교", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=11)

    plt.tight_layout()
    path = os.path.join(output_dir, "radar_chart.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


# ── 3. 항목별 박스플롯 ──────────────────────────────────────────
def plot_criteria_boxplot(results: list[dict], output_dir: str):
    """9개 평가 항목별 점수 박스플롯."""
    criteria_keys = list(EVALUATION_CRITERIA.keys())
    criteria_names = [EVALUATION_CRITERIA[k]["name"] for k in criteria_keys]
    max_scores = [EVALUATION_MAX_SCORES[k] for k in criteria_keys]

    all_scores = {k: [] for k in criteria_keys}
    for r in results:
        cs = r.get("criteria_scores", {})
        total = r.get("total_score", 0)
        if total == 0:
            continue
        for k in criteria_keys:
            score = 0
            if isinstance(cs.get(k), dict):
                score = cs[k].get("score", 0)
            elif isinstance(cs.get(k), (int, float)):
                score = cs[k]
            # 정규화 (0~100%)
            idx = criteria_keys.index(k)
            normalized = (score / max_scores[idx] * 100) if max_scores[idx] > 0 else 0
            all_scores[k].append(normalized)

    fig, ax = plt.subplots(figsize=(14, 6))

    data = [all_scores[k] for k in criteria_keys]
    bp = ax.boxplot(data, patch_artist=True, labels=criteria_names)

    colors_box = ["#3498db", "#2ecc71", "#e67e22", "#9b59b6", "#e74c3c",
                  "#1abc9c", "#f39c12", "#34495e", "#d35400"]
    for patch, color in zip(bp["boxes"], colors_box):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("정규화 점수 (%)", fontsize=12)
    ax.set_title("9개 평가 항목별 점수 분포", fontsize=14, fontweight="bold")
    ax.set_ylim(-5, 105)
    ax.axhline(y=50, color="gray", linestyle=":", alpha=0.5)
    plt.xticks(rotation=25, ha="right", fontsize=9)

    plt.tight_layout()
    path = os.path.join(output_dir, "criteria_boxplot.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")
    return path


# ── 4. CRAG 로그 분석 ──────────────────────────────────────────
def analyze_crag_logs(session_dir: str, output_dir: str) -> dict:
    """배치 세션의 CRAG 로그 파싱 및 통계."""
    meta_path = os.path.join(session_dir, "session_meta.json")
    crag_stats = {
        "total_queries": 0,
        "docs_retrieved": 0,
        "docs_passed": 0,
        "rewrites": 0,
        "web_fallbacks": 0,
        "no_retriever": 0,
    }

    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
            logs = meta.get("rag_grading_log", [])
    else:
        # 개별 파일에서 로그 수집
        logs = []
        for fname in sorted(os.listdir(session_dir)):
            if fname.endswith(".json") and fname != "session_meta.json":
                with open(os.path.join(session_dir, fname), encoding="utf-8") as f:
                    data = json.load(f)
                    logs.extend(data.get("rag_grading_log", []))

    for entry in logs:
        if "문서 검색됨" in entry:
            crag_stats["total_queries"] += 1
            try:
                num = int(entry.split(":")[1].strip().split("개")[0])
                crag_stats["docs_retrieved"] += num
            except (IndexError, ValueError):
                pass
        elif "관련 문서 통과" in entry:
            try:
                parts = entry.split(":")[-1].strip()
                passed = int(parts.split("/")[0])
                crag_stats["docs_passed"] += passed
            except (IndexError, ValueError):
                pass
        elif "쿼리 리라이트" in entry or "리라이트 쿼리" in entry:
            crag_stats["rewrites"] += 1
        elif "웹 검색으로 보완" in entry or "웹 검색 fallback" in entry:
            crag_stats["web_fallbacks"] += 1
        elif "retriever 없음" in entry:
            crag_stats["no_retriever"] += 1

    # 통과율 계산
    if crag_stats["docs_retrieved"] > 0:
        crag_stats["pass_rate"] = round(
            crag_stats["docs_passed"] / crag_stats["docs_retrieved"] * 100, 1
        )
    else:
        crag_stats["pass_rate"] = 0.0

    crag_stats["raw_logs"] = logs

    # CRAG 통계 차트
    if crag_stats["total_queries"] > 0:
        _plot_crag_stats(crag_stats, output_dir)

    return crag_stats


def _plot_crag_stats(stats: dict, output_dir: str):
    """CRAG 파이프라인 통계 차트."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 좌: 검색 결과 분포
    labels = ["관련 문서 통과", "비관련 (필터링)", "웹 검색 fallback"]
    sizes = [
        stats["docs_passed"],
        stats["docs_retrieved"] - stats["docs_passed"],
        stats["web_fallbacks"],
    ]
    # 0인 항목 제거
    non_zero = [(l, s) for l, s in zip(labels, sizes) if s > 0]
    if non_zero:
        labels_nz, sizes_nz = zip(*non_zero)
        colors = ["#2ecc71", "#e74c3c", "#3498db"][:len(non_zero)]
        axes[0].pie(sizes_nz, labels=labels_nz, autopct="%1.1f%%", colors=colors,
                    startangle=90, textprops={"fontsize": 10})
    axes[0].set_title("Corrective RAG 문서 필터링 결과", fontsize=12, fontweight="bold")

    # 우: CRAG 파이프라인 흐름
    stages = ["검색 쿼리", "문서 검색됨", "관련 문서 통과", "쿼리 리라이트", "웹 fallback"]
    values = [
        stats["total_queries"],
        stats["docs_retrieved"],
        stats["docs_passed"],
        stats["rewrites"],
        stats["web_fallbacks"],
    ]
    bars = axes[1].barh(stages, values, color=["#3498db", "#2ecc71", "#27ae60", "#f39c12", "#e74c3c"])
    axes[1].set_xlabel("건수", fontsize=11)
    axes[1].set_title("CRAG 파이프라인 단계별 통계", fontsize=12, fontweight="bold")
    axes[1].invert_yaxis()
    for bar, val in zip(bars, values):
        axes[1].text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     str(val), va="center", fontsize=10, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(output_dir, "crag_analysis.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  → {path}")


# ── 5. 종합 리포트 ─────────────────────────────────────────────
def generate_evidence_report(
    results: list[dict],
    crag_stats: dict,
    ragas_path: str | None,
    output_dir: str,
):
    """종합 증빙자료 Markdown 리포트."""
    # 통계 계산
    valid = [r for r in results if r.get("total_score", 0) > 0]
    scores = [r["total_score"] for r in valid]
    invest_count = sum(1 for r in results if r.get("verdict") == "invest")
    reject_count = len(results) - invest_count
    domain_reject = sum(1 for r in results if r.get("total_score", 0) == 0)

    avg_score = np.mean(scores) if scores else 0
    std_score = np.std(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0

    lines = []
    lines.append("# VSco 시스템 평가 증빙자료\n")
    lines.append(f"**생성일**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**시스템**: LangGraph Multi-Agent + Corrective RAG")
    lines.append(f"**도메인**: Energy (배터리·ESS 중심)\n")

    lines.append("---\n")
    lines.append("## 1. 배치 평가 결과 요약\n")
    lines.append(f"- **평가 대상**: {len(results)}개 스타트업")
    lines.append(f"- **투자 추천(invest)**: {invest_count}개")
    lines.append(f"- **기각(reject)**: {reject_count}개 (도메인 부적합 {domain_reject}개 포함)")
    lines.append(f"- **투자 판단 기준선**: {INVESTMENT_THRESHOLD}점\n")
    lines.append(f"### 점수 통계 (도메인 적합 스타트업)")
    lines.append(f"- 평균: **{avg_score:.1f}점**")
    lines.append(f"- 표준편차: {std_score:.1f}")
    lines.append(f"- 범위: {min_score} ~ {max_score}")

    lines.append(f"\n### 스타트업별 점수")
    lines.append("| # | 스타트업 | 총점 | 판정 |")
    lines.append("|---|---------|------|------|")
    sorted_results = sorted(results, key=lambda x: x.get("total_score", 0), reverse=True)
    for i, r in enumerate(sorted_results, 1):
        name = r.get("startup_name") or r.get("company_name", "?")
        score = r.get("total_score", 0)
        verdict = r.get("verdict", "reject")
        mark = "INVEST" if verdict == "invest" else "REJECT"
        lines.append(f"| {i} | {name} | {score} | {mark} |")

    lines.append("\n![점수 분포](score_distribution.png)\n")
    lines.append("![레이더 차트](radar_chart.png)\n")
    lines.append("![항목별 박스플롯](criteria_boxplot.png)\n")

    # 항목별 분석
    lines.append("---\n")
    lines.append("## 2. 9개 평가 항목 횡단 분석\n")

    criteria_keys = list(EVALUATION_CRITERIA.keys())
    for k in criteria_keys:
        name = EVALUATION_CRITERIA[k]["name"]
        max_s = EVALUATION_MAX_SCORES[k]
        item_scores = []
        for r in valid:
            cs = r.get("criteria_scores", {})
            if isinstance(cs.get(k), dict):
                item_scores.append(cs[k].get("score", 0))
            elif isinstance(cs.get(k), (int, float)):
                item_scores.append(cs[k])

        if item_scores:
            avg_item = np.mean(item_scores)
            lines.append(f"- **{name}** ({max_s}점 만점): 평균 {avg_item:.1f}점 ({avg_item / max_s * 100:.0f}%)")

    lines.append("\n---\n")
    lines.append("## 3. Corrective RAG 파이프라인 분석\n")
    lines.append(f"- 총 RAG 검색 쿼리: {crag_stats['total_queries']}건")
    lines.append(f"- 검색된 문서 수: {crag_stats['docs_retrieved']}건")
    lines.append(f"- 관련성 필터 통과: {crag_stats['docs_passed']}건 (**통과율 {crag_stats['pass_rate']}%**)")
    lines.append(f"- 쿼리 리라이트 발동: {crag_stats['rewrites']}건")
    lines.append(f"- 웹 검색 fallback: {crag_stats['web_fallbacks']}건")
    lines.append("\n![CRAG 분석](crag_analysis.png)\n")

    # RAGAS 결과 포함
    if ragas_path and os.path.exists(ragas_path):
        with open(ragas_path, encoding="utf-8") as f:
            ragas = json.load(f)
        lines.append("---\n")
        lines.append("## 4. RAGAS RAG 품질 평가\n")
        lines.append(f"- 평가 질문 수: {ragas['num_questions']}개\n")
        lines.append("| 메트릭 | 점수 |")
        lines.append("|--------|------|")
        for metric_name, info in ragas.get("metrics", {}).items():
            lines.append(f"| {info['display_name']} | **{info['average']:.4f}** |")
    else:
        lines.append("---\n")
        lines.append("## 4. RAGAS RAG 품질 평가\n")
        lines.append("_RAGAS 평가가 아직 실행되지 않았습니다. `evaluation/ragas_eval.py`를 실행하세요._\n")

    lines.append("\n---\n")
    lines.append("## 5. 시스템 아키텍처\n")
    lines.append("```")
    lines.append("┌─────────────────────────────────────────────────┐")
    lines.append("│              VSco 투자 평가 시스템               │")
    lines.append("├─────────────────────────────────────────────────┤")
    lines.append("│                                                 │")
    lines.append("│  [Startup Search] ──→ [Domain Check]            │")
    lines.append("│        │                    │                   │")
    lines.append("│        ▼                    ▼                   │")
    lines.append("│  ┌──────────┐  ┌────────────────┐              │")
    lines.append("│  │Tech Anal.│  │Market/Policy   │  (병렬 + RAG)│")
    lines.append("│  │  + CRAG  │  │  + CRAG        │              │")
    lines.append("│  └────┬─────┘  └───────┬────────┘              │")
    lines.append("│       └────────┬───────┘                       │")
    lines.append("│                ▼                                │")
    lines.append("│       [Competitor Analysis] (웹 검색)           │")
    lines.append("│                │                                │")
    lines.append("│                ▼                                │")
    lines.append("│    [Investment Decision + CRAG]                 │")
    lines.append("│       9항목 가중합 = 100점                      │")
    lines.append("│                │                                │")
    lines.append("│                ▼                                │")
    lines.append("│       [Evaluation Check]                       │")
    lines.append("│                │                                │")
    lines.append("│                ▼                                │")
    lines.append("│         [Report Writer]                        │")
    lines.append("│                                                 │")
    lines.append("├─────────────────────────────────────────────────┤")
    lines.append("│ RAG: FAISS(bge-m3) + Corrective RAG            │")
    lines.append("│ LLM: GPT-4o-mini  │ 검색: Tavily              │")
    lines.append("│ 문서: 4 PDF (174 chunks)                       │")
    lines.append("└─────────────────────────────────────────────────┘")
    lines.append("```")

    report_path = os.path.join(output_dir, "evidence_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  → {report_path}")

    # PDF 생성
    pdf_path = _generate_pdf(output_dir, "\n".join(lines))

    return report_path


def _generate_pdf(output_dir: str, md_content: str):
    """Markdown 리포트를 PDF로 변환 (이미지 포함)."""
    import markdown
    from weasyprint import HTML

    # Markdown → HTML
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code"],
    )

    # 이미지 경로를 절대 경로로 변환
    abs_dir = os.path.abspath(output_dir)
    for img in ["score_distribution.png", "radar_chart.png", "criteria_boxplot.png", "crag_analysis.png"]:
        img_path = os.path.join(abs_dir, img)
        if os.path.exists(img_path):
            html_body = html_body.replace(f'src="{img}"', f'src="file://{img_path}"')
            # alt 텍스트 기반 img 태그도 처리
            html_body = html_body.replace(
                f'<img alt="{img.replace(".png", "").replace("_", " ")}"',
                f'<img alt="{img}"'
            )

    html_full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 2cm; }}
    body {{
        font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #333;
    }}
    h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; font-size: 18pt; }}
    h2 {{ color: #2c3e50; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 20px; font-size: 14pt; }}
    h3 {{ color: #34495e; font-size: 12pt; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; }}
    th {{ background-color: #2c3e50; color: white; padding: 8px; text-align: left; }}
    td {{ border: 1px solid #ddd; padding: 6px 8px; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    img {{ max-width: 100%; height: auto; margin: 15px 0; }}
    code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 9pt; }}
    pre {{ background: #f4f4f4; padding: 12px; border-radius: 5px; overflow-x: auto; font-size: 8pt; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 15px 0; }}
    strong {{ color: #2c3e50; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    pdf_path = os.path.join(output_dir, "evidence_report.pdf")
    HTML(string=html_full, base_url=abs_dir).write_pdf(pdf_path)
    print(f"  → {pdf_path}")
    return pdf_path


def main():
    # 세션 디렉토리 결정
    if len(sys.argv) > 1:
        session_dir = sys.argv[1]
    else:
        session_dir = find_latest_batch_session()

    print("=" * 60)
    print("VSco 증빙자료 생성")
    print(f"배치 세션: {session_dir}")
    print("=" * 60)

    # 출력 디렉토리
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"outputs/evidence_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # 1. 배치 결과 로드
    print("\n[1/5] 배치 결과 로드...")
    results = load_batch_results(session_dir)
    print(f"  → {len(results)}개 스타트업 로드")

    # 2. 차트 생성
    print("\n[2/5] 점수 분포 차트 생성...")
    plot_score_distribution(results, output_dir)

    print("\n[3/5] 레이더 차트 + 박스플롯 생성...")
    plot_radar_chart(results, output_dir)
    plot_criteria_boxplot(results, output_dir)

    # 3. CRAG 로그 분석
    print("\n[4/5] CRAG 로그 분석...")
    crag_stats = analyze_crag_logs(session_dir, output_dir)

    # 4. RAGAS 결과 찾기 (있으면 포함)
    ragas_path = None
    ragas_dirs = sorted(
        [d for d in os.listdir(RAGAS_RESULTS_DIR) if d.startswith("ragas_eval_")],
        reverse=True,
    ) if os.path.exists(RAGAS_RESULTS_DIR) else []
    if ragas_dirs:
        candidate = os.path.join(RAGAS_RESULTS_DIR, ragas_dirs[0], "ragas_results.json")
        if os.path.exists(candidate):
            ragas_path = candidate
            print(f"  → RAGAS 결과 발견: {ragas_path}")

    # 5. 종합 리포트
    print("\n[5/5] 종합 증빙자료 리포트 생성...")
    generate_evidence_report(results, crag_stats, ragas_path, output_dir)

    print(f"\n{'=' * 60}")
    print(f"증빙자료 생성 완료: {output_dir}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
