"""Ablation Study 시각화: RAG ON vs RAG OFF 다면 비교 차트."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.gridspec as gridspec
import numpy as np

from config import INVESTMENT_THRESHOLD

# 한글 폰트
for fp in [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
        prop = fm.FontProperties(fname=fp)
        plt.rcParams["font.family"] = prop.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

# ── 데이터 ──
CRITERIA_LABELS = {
    "sk_synergy": "SK 시너지\n(15)",
    "market_size_growth": "시장규모\n(17)",
    "problem_solving": "문제해결\n(10)",
    "willingness_to_pay": "지불의사\n(8)",
    "tech_differentiation": "기술차별화\n(14)",
    "scalability": "확장성\n(10)",
    "revenue_model": "수익모델\n(8)",
    "risk": "리스크\n(6)",
    "founder_team": "팀역량\n(12)",
}

CRITERIA_MAX = {
    "sk_synergy": 15,
    "market_size_growth": 17,
    "problem_solving": 10,
    "willingness_to_pay": 8,
    "tech_differentiation": 14,
    "scalability": 10,
    "revenue_model": 8,
    "risk": 6,
    "founder_team": 12,
}

CRITERIA_ORDER = list(CRITERIA_LABELS.keys())


def load_session(session_dir: str) -> dict[str, dict]:
    results = {}
    for f in sorted(os.listdir(session_dir)):
        if f.endswith(".json") and f not in ("session_meta.json", "ablation_comparison.json"):
            with open(os.path.join(session_dir, f), encoding="utf-8") as fh:
                d = json.load(fh)
                name = d.get("company_name", "")
                if name and d.get("total_score", 0) > 0:
                    results[name] = d
    return results


def generate_ablation_viz(ref_dir: str, abl_dir: str, output_path: str):
    ref = load_session(ref_dir)
    abl = load_session(abl_dir)
    common = sorted(set(ref) & set(abl), key=lambda n: ref[n]["total_score"], reverse=True)

    # ── 색상 팔레트 ──
    C_ON = "#2ecc71"
    C_OFF = "#e74c3c"
    C_ON_DARK = "#27ae60"
    C_OFF_DARK = "#c0392b"
    C_THRESH = "#3498db"
    C_BG = "#fafbfc"
    C_GRID = "#e0e0e0"

    # ── Figure: 2행 2열 ──
    fig = plt.figure(figsize=(20, 16), facecolor="white")
    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3,
                           left=0.06, right=0.96, top=0.92, bottom=0.06)

    fig.suptitle("Ablation Study: RAG ON vs RAG OFF 비교 분석",
                 fontsize=20, fontweight="bold", y=0.97)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1) 총점 비교 막대 그래프
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_BG)

    x = np.arange(len(common))
    w = 0.35
    on_scores = [ref[n]["total_score"] for n in common]
    off_scores = [abl[n]["total_score"] for n in common]

    bars_on = ax1.bar(x - w/2, on_scores, w, label="RAG ON", color=C_ON,
                      edgecolor="white", linewidth=0.8, zorder=3)
    bars_off = ax1.bar(x + w/2, off_scores, w, label="RAG OFF", color=C_OFF,
                       edgecolor="white", linewidth=0.8, zorder=3)

    ax1.axhline(y=INVESTMENT_THRESHOLD, color=C_THRESH, linestyle="--",
                linewidth=2, label=f"Invest Threshold ({int(INVESTMENT_THRESHOLD)}점)", zorder=2)

    # 점수 라벨
    for bar, color in [(bars_on, C_ON_DARK), (bars_off, C_OFF_DARK)]:
        for b in bar:
            ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 0.8,
                     str(int(b.get_height())), ha="center", va="bottom",
                     fontsize=9, fontweight="bold", color=color)

    # 판정 변경 표시
    for i, name in enumerate(common):
        rv = ref[name].get("verdict", "")
        av = abl[name].get("verdict", "")
        if rv != av:
            label = f"판정 변경!\n{rv.upper()}→{av.upper()}"
            ax1.annotate(label,
                         xy=(i, max(on_scores[i], off_scores[i]) + 3),
                         fontsize=8, fontweight="bold", color="#e67e22", ha="center",
                         bbox=dict(boxstyle="round,pad=0.3", fc="#ffeaa7", ec="#e67e22", alpha=0.9))

    ax1.set_xticks(x)
    ax1.set_xticklabels(common, rotation=30, ha="right", fontsize=8)
    ax1.set_ylabel("총점 (100점 만점)", fontsize=11)
    ax1.set_title("① 스타트업별 총점 비교", fontsize=13, fontweight="bold", pad=10)
    ax1.set_ylim(0, 78)
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(axis="y", alpha=0.3, color=C_GRID, zorder=1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2) 항목별 평균 점수 비교 (정규화)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_BG)

    def _score(data: dict, criteria: str) -> int:
        v = data.get("criteria_scores", {}).get(criteria, {})
        return v.get("score", 0) if isinstance(v, dict) else int(v)

    on_means = []
    off_means = []
    for c in CRITERIA_ORDER:
        on_vals = [_score(ref[n], c) for n in common]
        off_vals = [_score(abl[n], c) for n in common]
        mx = CRITERIA_MAX[c]
        on_means.append(np.mean(on_vals) / mx * 100)
        off_means.append(np.mean(off_vals) / mx * 100)

    y = np.arange(len(CRITERIA_ORDER))
    h = 0.35
    ax2.barh(y + h/2, on_means, h, label="RAG ON", color=C_ON, edgecolor="white", zorder=3)
    ax2.barh(y - h/2, off_means, h, label="RAG OFF", color=C_OFF, edgecolor="white", zorder=3)

    # 차이 표시
    for i, (on_m, off_m) in enumerate(zip(on_means, off_means)):
        diff = on_m - off_m
        sign = "+" if diff > 0 else ""
        color = C_ON_DARK if diff > 0 else C_OFF_DARK
        ax2.text(max(on_m, off_m) + 1.5, i, f"{sign}{diff:.1f}%p",
                 va="center", fontsize=8, fontweight="bold", color=color)

    labels = [CRITERIA_LABELS[c] for c in CRITERIA_ORDER]
    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=8)
    ax2.set_xlabel("정규화 점수 (%)", fontsize=11)
    ax2.set_title("② 평가 항목별 평균 점수 (정규화)", fontsize=13, fontweight="bold", pad=10)
    ax2.set_xlim(0, 85)
    ax2.legend(fontsize=9, loc="lower right")
    ax2.grid(axis="x", alpha=0.3, color=C_GRID, zorder=1)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3) 스탠다드에너지 사례 분석 (레이더 차트)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    ax3 = fig.add_subplot(gs[1, 0], polar=True)

    # 스탠다드에너지 데이터 (판정 변경 사례)
    target = "스탠다드에너지"
    angles = np.linspace(0, 2 * np.pi, len(CRITERIA_ORDER), endpoint=False).tolist()
    angles += angles[:1]

    ref_vals = []
    abl_vals = []
    for c in CRITERIA_ORDER:
        mx = CRITERIA_MAX[c]
        ref_vals.append(_score(ref[target], c) / mx * 100)
        abl_vals.append(_score(abl[target], c) / mx * 100)
    ref_vals += ref_vals[:1]
    abl_vals += abl_vals[:1]

    ax3.plot(angles, ref_vals, "o-", color=C_ON, linewidth=2, markersize=6, label="RAG ON (61점, INVEST)")
    ax3.fill(angles, ref_vals, alpha=0.15, color=C_ON)
    ax3.plot(angles, abl_vals, "s-", color=C_OFF, linewidth=2, markersize=6, label="RAG OFF (58점, REJECT)")
    ax3.fill(angles, abl_vals, alpha=0.15, color=C_OFF)

    ax3.set_xticks(angles[:-1])
    short_labels = [l.split("\n")[0] for l in labels]
    ax3.set_xticklabels(short_labels, fontsize=8)
    ax3.set_ylim(0, 100)
    ax3.set_yticks([20, 40, 60, 80])
    ax3.set_yticklabels(["20%", "40%", "60%", "80%"], fontsize=7, color="#888")
    ax3.set_title("③ 스탠다드에너지 항목별 비교\n(판정 변경: INVEST → REJECT)",
                  fontsize=13, fontweight="bold", pad=25)
    ax3.legend(fontsize=9, loc="upper right", bbox_to_anchor=(1.3, 1.15))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4) 점수 차이 히트맵 (RAG ON - RAG OFF)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
    ax4 = fig.add_subplot(gs[1, 1])

    diff_matrix = []
    for n in common:
        row = []
        for c in CRITERIA_ORDER:
            on_v = _score(ref[n], c)
            off_v = _score(abl[n], c)
            row.append(on_v - off_v)
        diff_matrix.append(row)

    diff_arr = np.array(diff_matrix)
    vmax = max(abs(diff_arr.min()), abs(diff_arr.max()), 3)

    im = ax4.imshow(diff_arr, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

    ax4.set_xticks(range(len(CRITERIA_ORDER)))
    ax4.set_xticklabels(short_labels, rotation=45, ha="right", fontsize=8)
    ax4.set_yticks(range(len(common)))
    ax4.set_yticklabels(common, fontsize=8)

    # 셀 값 표시
    for i in range(len(common)):
        for j in range(len(CRITERIA_ORDER)):
            val = diff_arr[i, j]
            color = "white" if abs(val) >= vmax * 0.7 else "black"
            sign = "+" if val > 0 else ""
            ax4.text(j, i, f"{sign}{int(val)}", ha="center", va="center",
                     fontsize=9, fontweight="bold", color=color)

    cbar = fig.colorbar(im, ax=ax4, shrink=0.8, pad=0.02)
    cbar.set_label("점수 차이 (RAG ON - OFF)", fontsize=9)
    ax4.set_title("④ 항목별 점수 차이 히트맵", fontsize=13, fontweight="bold", pad=10)

    # ── 하단 요약 텍스트 ──
    on_avg = np.mean(on_scores)
    off_avg = np.mean(off_scores)
    diff_avg = on_avg - off_avg
    invest_on = sum(1 for n in common if ref[n].get("verdict") == "invest")
    invest_off = sum(1 for n in common if abl[n].get("verdict") == "invest")

    summary = (
        f"평균: RAG ON {on_avg:.1f}점 vs RAG OFF {off_avg:.1f}점 (차이 {diff_avg:+.1f}점)  |  "
        f"Invest 판정: RAG ON {invest_on}개 vs RAG OFF {invest_off}개  |  "
        f"RAG = 도메인 벤치마크 기반 보수적·정확한 평가"
    )
    fig.text(0.5, 0.01, summary, ha="center", fontsize=11, style="italic", color="#555")

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"차트 저장: {output_path}")


if __name__ == "__main__":
    ref_dir = "outputs/batch_results/20260312_201127"
    abl_dir = "outputs/batch_results/ablation_ragoff_20260313_074047"
    output = "outputs/ablation_results/ablation_comparison_detailed.png"
    generate_ablation_viz(ref_dir, abl_dir, output)
