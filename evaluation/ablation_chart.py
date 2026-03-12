"""Ablation Study 시각화: RAG ON vs RAG OFF 비교 차트."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

from config import INVESTMENT_THRESHOLD

# 한글 폰트
for fp in ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"]:
    if os.path.exists(fp):
        fm.fontManager.addfont(fp)
        prop = fm.FontProperties(fname=fp)
        plt.rcParams["font.family"] = prop.get_name()
        break
plt.rcParams["axes.unicode_minus"] = False


def load_results(session_dir: str) -> dict[str, dict]:
    results = {}
    for f in sorted(os.listdir(session_dir)):
        if f.endswith(".json") and f != "session_meta.json":
            with open(os.path.join(session_dir, f), encoding="utf-8") as fh:
                d = json.load(fh)
                name = d.get("company_name", "")
                if name and d.get("total_score", 0) > 0:
                    results[name] = d
    return results


def generate_ablation_chart(ref_dir: str, abl_dir: str, output_path: str):
    ref = load_results(ref_dir)
    abl = load_results(abl_dir)

    # 공통 스타트업만
    common = sorted(set(ref.keys()) & set(abl.keys()), key=lambda n: ref[n]["total_score"], reverse=True)

    names = common
    on_scores = [ref[n]["total_score"] for n in names]
    off_scores = [abl[n]["total_score"] for n in names]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = np.arange(len(names))
    width = 0.35

    bars_on = ax.bar(x - width / 2, on_scores, width, label="RAG ON", color="#2ecc71", edgecolor="white", zorder=3)
    bars_off = ax.bar(x + width / 2, off_scores, width, label="RAG OFF", color="#e74c3c", edgecolor="white", zorder=3)

    # Threshold 선
    ax.axhline(y=INVESTMENT_THRESHOLD, color="#3498db", linestyle="--", linewidth=2, label=f"Invest Threshold ({int(INVESTMENT_THRESHOLD)}점)", zorder=2)

    # 스탠다드에너지 하이라이트
    for i, name in enumerate(names):
        ref_v = ref[name].get("verdict", "")
        abl_v = abl[name].get("verdict", "")
        if ref_v != abl_v:
            ax.annotate(
                "판정 변경!\nINVEST→REJECT",
                xy=(i, max(on_scores[i], off_scores[i]) + 1),
                fontsize=9,
                fontweight="bold",
                color="#e67e22",
                ha="center",
                va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffeaa7", edgecolor="#e67e22", alpha=0.9),
            )

    # 점수 라벨
    for bar in bars_on:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9, fontweight="bold", color="#27ae60")
    for bar in bars_off:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(int(bar.get_height())), ha="center", va="bottom", fontsize=9, fontweight="bold", color="#c0392b")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("총점 (100점 만점)", fontsize=12)
    ax.set_title("Ablation Study: RAG ON vs RAG OFF 비교", fontsize=15, fontweight="bold")
    ax.set_ylim(0, 75)
    ax.legend(fontsize=11, loc="upper right")
    ax.grid(axis="y", alpha=0.3, zorder=1)

    # 하단 요약 텍스트
    on_avg = np.mean(on_scores)
    off_avg = np.mean(off_scores)
    diff = on_avg - off_avg
    invest_on = sum(1 for n in names if ref[n].get("verdict") == "invest")
    invest_off = sum(1 for n in names if abl[n].get("verdict") == "invest")

    summary = (
        f"평균: RAG ON {on_avg:.1f}점 vs RAG OFF {off_avg:.1f}점 (차이 {diff:+.1f}점)  |  "
        f"Invest: RAG ON {invest_on}개 vs RAG OFF {invest_off}개  |  "
        f"RAG = 벤치마크 기반 보수적 평가 + 정확한 가점"
    )
    fig.text(0.5, 0.01, summary, ha="center", fontsize=10, style="italic", color="#555")

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.15)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"차트 저장: {output_path}")


if __name__ == "__main__":
    ref_dir = "outputs/batch_results/20260312_201127"
    abl_dir = "outputs/batch_results/ablation_ragoff_20260313_074047"
    output = "outputs/ablation_results/ablation_comparison.png"
    generate_ablation_chart(ref_dir, abl_dir, output)
