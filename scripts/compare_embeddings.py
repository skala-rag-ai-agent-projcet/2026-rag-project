"""
Embedding Model Comparison: BAAI/bge-m3 vs upskyy/bge-m3-korean

동일 청크셋에 대해 두 임베딩 모델의 검색 품질을 비교 평가.
- Cosine Similarity 분포
- Top-k overlap (Jaccard)
- LLM Judge (GPT-4o-mini) 관련성 평가
- 카테고리별(기술/시장/경쟁사) 성능 비교
"""

import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import DATA_DIR, OPENAI_API_KEY

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODELS = {
    "bge-m3": "BAAI/bge-m3",
    "bge-m3-ko": "upskyy/bge-m3-korean",
}
TOP_K = 5
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "embedding_comparison")

# 한글 폰트
plt.rcParams["font.family"] = "Apple SD Gothic Neo"
plt.rcParams["axes.unicode_minus"] = False

# ── 테스트 쿼리셋 (실제 에이전트 패턴 기반) ─────────────────────────────────
QUERIES = {
    "tech": [
        "바나듐 레독스 플로우 배터리 에너지 밀도 효율 성능",
        "수소 연료전지 스택 기술 내구성 사양",
        "ESS 배터리 관리 시스템 BMS 안전 기술",
        "리튬인산철 LFP 배터리 사이클 수명 비교",
        "에너지 저장 시스템 충방전 효율 기술 차별성",
    ],
    "market": [
        "에너지 저장 시장 규모 성장률 TAM SAM SOM",
        "수소경제 정책 IRA 보조금 시장 전망 2025",
        "배터리 ESS 시장 글로벌 성장 전망",
        "재생에너지 연계 에너지 저장 수요 전망",
        "한국 에너지 전환 정책 탄소중립 투자 규모",
    ],
    "competitor": [
        "레독스 플로우 배터리 경쟁사 시장 점유율 비교",
        "수소 연료전지 스타트업 경쟁 환경 진입장벽",
        "ESS 배터리 제조사 경쟁 구도 대체기술",
        "에너지 스타트업 투자 유치 실적 비교",
        "SK 에너지 밸류체인 시너지 배터리 협력사",
    ],
}

ALL_QUERIES = []
QUERY_CATEGORIES = []
for cat, qs in QUERIES.items():
    for q in qs:
        ALL_QUERIES.append(q)
        QUERY_CATEGORIES.append(cat)


# ── 1. 문서 로딩 + 청킹 ──────────────────────────────────────────────────────
def load_documents():
    """data/ 디렉토리의 PDF/MD 파일을 로드하고 청킹."""
    documents = []

    for fname in sorted(os.listdir(DATA_DIR)):
        fpath = os.path.join(DATA_DIR, fname)
        if fname.endswith(".pdf"):
            docs = PyPDFLoader(fpath).load()
            documents.extend(docs)
            print(f"  로드: {fname} ({len(docs)} pages)")
        elif fname.endswith(".md"):
            docs = TextLoader(fpath, encoding="utf-8").load()
            documents.extend(docs)
            print(f"  로드: {fname}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    print(f"  → 총 {len(chunks)}개 청크 생성\n")
    return chunks


# ── 2. 모델별 벡터스토어 구축 ─────────────────────────────────────────────────
def build_vectorstore(model_name: str, chunks):
    """주어진 모델로 FAISS 벡터스토어 구축."""
    print(f"  [{model_name}] 임베딩 생성 중...")
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vs = FAISS.from_documents(chunks, embeddings)
    print(f"  [{model_name}] 벡터스토어 구축 완료")
    return vs


# ── 3. 검색 비교 ─────────────────────────────────────────────────────────────
def run_retrieval_comparison(vectorstores: dict):
    """15쿼리 × 2모델 검색 → similarity score + top-k overlap 수집."""
    results = []

    for i, query in enumerate(ALL_QUERIES):
        cat = QUERY_CATEGORIES[i]
        row = {"query": query, "category": cat}

        retrieved_docs = {}
        for label, vs in vectorstores.items():
            docs_with_scores = vs.similarity_search_with_score(query, k=TOP_K)
            scores = [1 - s for s in [score for _, score in docs_with_scores]]  # FAISS L2 → similarity
            contents = [doc.page_content[:200] for doc, _ in docs_with_scores]

            row[f"{label}_avg_sim"] = float(np.mean(scores))
            row[f"{label}_max_sim"] = float(np.max(scores))
            row[f"{label}_scores"] = scores
            row[f"{label}_contents"] = contents
            retrieved_docs[label] = set(
                doc.page_content[:100] for doc, _ in docs_with_scores
            )

        # Jaccard overlap
        sets = list(retrieved_docs.values())
        intersection = sets[0] & sets[1]
        union = sets[0] | sets[1]
        row["jaccard_overlap"] = len(intersection) / len(union) if union else 0.0

        results.append(row)
        print(f"  [{i+1}/{len(ALL_QUERIES)}] {cat}: {query[:30]}...")

    return results


# ── 4. LLM Judge 관련성 평가 ──────────────────────────────────────────────────
def llm_judge_relevance(results: list):
    """GPT-4o-mini로 각 검색 결과의 관련성 평가 (0-2점)."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
    model_labels = list(MODELS.keys())

    for i, row in enumerate(results):
        query = row["query"]
        for label in model_labels:
            contents = row.get(f"{label}_contents", [])
            chunks_text = "\n---\n".join(
                f"[Chunk {j+1}] {c}" for j, c in enumerate(contents)
            )

            prompt = f"""당신은 검색 품질 평가자입니다.

쿼리: "{query}"

아래는 검색된 상위 {TOP_K}개 문서 청크입니다:
{chunks_text}

각 청크의 쿼리 관련성을 0-2점으로 평가하세요:
- 0: 무관 (쿼리와 관련 없음)
- 1: 부분 관련 (일부 관련 정보 포함)
- 2: 높은 관련 (쿼리에 직접 답변 가능)

JSON 배열로만 응답하세요. 예: [2, 1, 0, 1, 2]"""

            response = llm.invoke(prompt)
            content = response.content.strip()

            # JSON 파싱
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.split("```")[0].strip()

            try:
                scores = json.loads(content)
                if not isinstance(scores, list):
                    scores = [1] * TOP_K
            except (json.JSONDecodeError, ValueError):
                scores = [1] * TOP_K

            # TOP_K개로 맞춤
            scores = (scores + [0] * TOP_K)[:TOP_K]
            row[f"{label}_relevance"] = scores
            row[f"{label}_avg_relevance"] = float(np.mean(scores))

        print(
            f"  [{i+1}/{len(results)}] LLM Judge 완료: {query[:30]}..."
        )

    return results


# ── 5. 시각화 ─────────────────────────────────────────────────────────────────
def plot_similarity_bar(results: list):
    """쿼리별 평균 유사도 비교 막대 차트."""
    fig, ax = plt.subplots(figsize=(14, 6))
    labels = list(MODELS.keys())
    x = np.arange(len(results))
    width = 0.35

    for j, label in enumerate(labels):
        vals = [r[f"{label}_avg_sim"] for r in results]
        ax.bar(x + j * width, vals, width, label=label, alpha=0.85)

    ax.set_xlabel("쿼리")
    ax.set_ylabel("평균 코사인 유사도")
    ax.set_title("쿼리별 평균 유사도 비교 (bge-m3 vs bge-m3-ko)")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(
        [f"Q{i+1}" for i in range(len(results))], rotation=0
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "similarity_bar_chart.png"), dpi=150)
    plt.close(fig)
    print("  → similarity_bar_chart.png")


def plot_similarity_box(results: list):
    """모델별 유사도 분포 박스플롯."""
    fig, ax = plt.subplots(figsize=(8, 6))
    labels = list(MODELS.keys())
    data = []
    for label in labels:
        all_scores = []
        for r in results:
            all_scores.extend(r[f"{label}_scores"])
        data.append(all_scores)

    bp = ax.boxplot(data, labels=labels, patch_artist=True)
    colors = ["#4C72B0", "#DD8452"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_ylabel("코사인 유사도")
    ax.set_title("모델별 유사도 분포")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "similarity_box_plot.png"), dpi=150)
    plt.close(fig)
    print("  → similarity_box_plot.png")


def plot_relevance_heatmap(results: list):
    """쿼리×모델 LLM Judge 관련성 히트맵."""
    labels = list(MODELS.keys())
    data = np.array(
        [[r[f"{label}_avg_relevance"] for label in labels] for r in results]
    )

    fig, ax = plt.subplots(figsize=(6, 10))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=2)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_yticks(range(len(results)))
    ax.set_yticklabels(
        [f"Q{i+1} ({QUERY_CATEGORIES[i]})" for i in range(len(results))]
    )

    for i in range(len(results)):
        for j in range(len(labels)):
            ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", fontsize=9)

    ax.set_title("LLM Judge 관련성 점수 (0-2)")
    fig.colorbar(im, ax=ax, shrink=0.6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "relevance_heatmap.png"), dpi=150)
    plt.close(fig)
    print("  → relevance_heatmap.png")


def plot_radar_chart(results: list):
    """카테고리별 성능 레이더 차트."""
    labels_model = list(MODELS.keys())
    categories = ["tech", "market", "competitor"]
    cat_labels = ["기술", "시장", "경쟁사"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), subplot_kw=dict(polar=True))

    # 메트릭: avg_sim, avg_relevance
    metrics = [
        ("avg_sim", "평균 유사도"),
        ("avg_relevance", "LLM 관련성"),
    ]

    for ax_idx, (metric_suffix, metric_name) in enumerate(metrics):
        ax = axes[ax_idx]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        for label in labels_model:
            values = []
            for cat in categories:
                cat_results = [
                    r[f"{label}_{metric_suffix}"]
                    for r in results
                    if r["category"] == cat
                ]
                values.append(float(np.mean(cat_results)))
            values += values[:1]
            ax.plot(angles, values, "o-", linewidth=2, label=label)
            ax.fill(angles, values, alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(cat_labels)
        ax.set_title(metric_name, y=1.1, fontsize=13)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    fig.suptitle("카테고리별 성능 레이더 차트", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(
        os.path.join(OUTPUT_DIR, "radar_chart.png"), dpi=150, bbox_inches="tight"
    )
    plt.close(fig)
    print("  → radar_chart.png")


def plot_overlap_bar(results: list):
    """쿼리별 top-5 검색 겹침률 (Jaccard) 막대 차트."""
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(results))
    overlaps = [r["jaccard_overlap"] for r in results]
    colors = ["#4C72B0" if QUERY_CATEGORIES[i] == "tech"
              else "#DD8452" if QUERY_CATEGORIES[i] == "market"
              else "#55A868" for i in range(len(results))]

    ax.bar(x, overlaps, color=colors, alpha=0.85)
    ax.set_xlabel("쿼리")
    ax.set_ylabel("Jaccard 겹침률")
    ax.set_title("쿼리별 Top-5 검색 결과 겹침률")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Q{i+1}" for i in range(len(results))])
    ax.axhline(y=np.mean(overlaps), color="red", linestyle="--", alpha=0.5,
               label=f"평균: {np.mean(overlaps):.2f}")

    # 범례
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#4C72B0", label="기술"),
        Patch(facecolor="#DD8452", label="시장"),
        Patch(facecolor="#55A868", label="경쟁사"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "overlap_bar_chart.png"), dpi=150)
    plt.close(fig)
    print("  → overlap_bar_chart.png")


def plot_summary_table(results: list):
    """종합 비교 테이블 이미지."""
    labels = list(MODELS.keys())
    categories = ["tech", "market", "competitor"]

    rows = []
    for label in labels:
        row = [label]
        # 전체 평균 유사도
        avg_sim = np.mean([r[f"{label}_avg_sim"] for r in results])
        row.append(f"{avg_sim:.4f}")
        # 전체 평균 관련성
        avg_rel = np.mean([r[f"{label}_avg_relevance"] for r in results])
        row.append(f"{avg_rel:.2f}")
        # 카테고리별 관련성
        for cat in categories:
            cat_rel = np.mean(
                [r[f"{label}_avg_relevance"] for r in results if r["category"] == cat]
            )
            row.append(f"{cat_rel:.2f}")
        rows.append(row)

    # 평균 Jaccard
    avg_jaccard = np.mean([r["jaccard_overlap"] for r in results])

    col_labels = ["모델", "평균 유사도", "평균 관련성", "기술", "시장", "경쟁사"]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)

    # 헤더 스타일
    for j in range(len(col_labels)):
        table[0, j].set_facecolor("#4C72B0")
        table[0, j].set_text_props(color="white", fontweight="bold")

    # 승자 하이라이트
    for col_idx in range(1, len(col_labels)):
        vals = [float(rows[r][col_idx]) for r in range(len(rows))]
        winner = np.argmax(vals)
        table[winner + 1, col_idx].set_facecolor("#C8E6C9")

    ax.set_title(
        f"종합 비교 요약  |  Top-5 평균 Jaccard 겹침률: {avg_jaccard:.2f}",
        fontsize=13,
        pad=20,
    )
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "summary_table.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  → summary_table.png")


# ── 6. CSV 저장 + 콘솔 요약 ──────────────────────────────────────────────────
def export_csv(results: list):
    """원시 데이터 CSV 저장."""
    labels = list(MODELS.keys())
    fieldnames = [
        "query_id", "category", "query", "jaccard_overlap",
    ]
    for label in labels:
        fieldnames.extend([
            f"{label}_avg_sim", f"{label}_max_sim", f"{label}_avg_relevance",
        ])

    csv_path = os.path.join(OUTPUT_DIR, "raw_scores.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for i, r in enumerate(results):
            row = {
                "query_id": f"Q{i+1}",
                "category": r["category"],
                "query": r["query"],
                "jaccard_overlap": f"{r['jaccard_overlap']:.4f}",
            }
            for label in labels:
                row[f"{label}_avg_sim"] = f"{r[f'{label}_avg_sim']:.4f}"
                row[f"{label}_max_sim"] = f"{r[f'{label}_max_sim']:.4f}"
                row[f"{label}_avg_relevance"] = f"{r[f'{label}_avg_relevance']:.2f}"
            writer.writerow(row)

    print(f"  → raw_scores.csv")


def print_console_summary(results: list):
    """콘솔에 승자 추천 출력."""
    labels = list(MODELS.keys())
    print("\n" + "=" * 60)
    print("  EMBEDDING MODEL COMPARISON SUMMARY")
    print("=" * 60)

    wins = {label: 0 for label in labels}

    # 평균 유사도
    for label in labels:
        avg = np.mean([r[f"{label}_avg_sim"] for r in results])
        print(f"  {label:15s}  평균 유사도: {avg:.4f}")
    sim_winner = max(labels, key=lambda l: np.mean([r[f"{l}_avg_sim"] for r in results]))
    wins[sim_winner] += 1
    print(f"  → 유사도 승자: {sim_winner}")

    print()

    # 평균 관련성
    for label in labels:
        avg = np.mean([r[f"{label}_avg_relevance"] for r in results])
        print(f"  {label:15s}  평균 관련성: {avg:.2f}/2.00")
    rel_winner = max(labels, key=lambda l: np.mean([r[f"{l}_avg_relevance"] for r in results]))
    wins[rel_winner] += 1
    print(f"  → 관련성 승자: {rel_winner}")

    print()

    # 카테고리별
    for cat, cat_kr in [("tech", "기술"), ("market", "시장"), ("competitor", "경쟁사")]:
        cat_results = [r for r in results if r["category"] == cat]
        for label in labels:
            avg = np.mean([r[f"{label}_avg_relevance"] for r in cat_results])
            print(f"  {label:15s}  {cat_kr} 관련성: {avg:.2f}")
        cat_winner = max(
            labels,
            key=lambda l: np.mean([r[f"{l}_avg_relevance"] for r in cat_results]),
        )
        wins[cat_winner] += 1
        print(f"  → {cat_kr} 승자: {cat_winner}")
        print()

    # Jaccard
    avg_jaccard = np.mean([r["jaccard_overlap"] for r in results])
    print(f"  Top-5 평균 Jaccard 겹침률: {avg_jaccard:.2f}")
    print()

    # 최종 추천
    overall_winner = max(wins, key=wins.get)
    print(f"  ★ 종합 추천 모델: {overall_winner} ({wins[overall_winner]}/5 메트릭 승리)")
    print("=" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  Embedding Model Comparison")
    print("  bge-m3 vs bge-m3-ko")
    print("=" * 60)

    # 1. 문서 로딩
    print("\n[1/6] 문서 로딩 + 청킹")
    chunks = load_documents()

    # 2. 벡터스토어 구축
    print("[2/6] 벡터스토어 구축")
    vectorstores = {}
    for label, model_name in MODELS.items():
        vectorstores[label] = build_vectorstore(model_name, chunks)

    # 3. 검색 비교
    print("\n[3/6] 검색 비교 (15쿼리 × 2모델)")
    results = run_retrieval_comparison(vectorstores)

    # 4. LLM Judge
    print("\n[4/6] LLM Judge 관련성 평가")
    results = llm_judge_relevance(results)

    # 5. 시각화
    print("\n[5/6] 시각화 생성")
    plot_similarity_bar(results)
    plot_similarity_box(results)
    plot_relevance_heatmap(results)
    plot_radar_chart(results)
    plot_overlap_bar(results)
    plot_summary_table(results)

    # 6. CSV + 콘솔 요약
    print("\n[6/6] CSV 저장 + 콘솔 요약")
    export_csv(results)
    print_console_summary(results)

    print(f"\n출력 디렉토리: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
