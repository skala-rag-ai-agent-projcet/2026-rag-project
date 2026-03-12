"""Ablation Study: RAG OFF 배치 평가.

이전 배치와 동일한 스타트업 목록을 사용하되, retriever=None으로 설정하여
RAG 없이 웹 검색만으로 평가한 결과를 비교.

사용법:
  .venv/bin/python evaluation/ablation_rag_off.py [session_dir]
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from config import (
    BATCH_CHUNK_SIZE,
    BATCH_MAX_CONCURRENCY,
    BATCH_RESULTS_DIR,
    BATCH_TOTAL_TIMEOUT,
)
from app import _to_canonical, _save_result


def run_ablation(reference_session: str):
    """이전 세션의 스타트업 목록으로 RAG OFF 배치 실행."""
    from graph.batch_workflow import build_batch_graph

    # 1. 참조 세션에서 스타트업 목록 로드
    meta_path = os.path.join(reference_session, "session_meta.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    domain_fit = meta["domain_fit"]
    print("=" * 60)
    print("  Ablation Study: RAG OFF 배치 평가")
    print("=" * 60)
    print(f"  참조 세션: {meta['session_id']}")
    print(f"  평가 대상: {len(domain_fit)}개 스타트업 (동일 목록)")
    print(f"  RAG: OFF (retriever=None, 웹 검색 fallback)")
    print("=" * 60)

    # 2. 세션 디렉토리 생성
    session_id = "ablation_ragoff_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(BATCH_RESULTS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # 3. RAG OFF로 그래프 빌드
    print("\n[설정] 배치 그래프 구축 (retriever=None)...")
    batch_app = build_batch_graph(retriever=None)

    # 4. 청크 단위 병렬 평가
    chunk_size = BATCH_CHUNK_SIZE
    concurrency = min(chunk_size, BATCH_MAX_CONCURRENCY)
    total_eval = len(domain_fit)

    print(f"[실행] {total_eval}개 평가 시작 (청크 {chunk_size}개, 동시 {concurrency}개)\n")

    t_start = time.time()
    batch_id = 0

    for chunk_start in range(0, total_eval, chunk_size):
        elapsed = time.time() - t_start
        if elapsed >= BATCH_TOTAL_TIMEOUT:
            print(f"\n⏱ 타임아웃 도달. 중단.")
            break

        chunk_names = domain_fit[chunk_start : chunk_start + chunk_size]
        chunk_num = chunk_start // chunk_size + 1
        total_chunks = (total_eval + chunk_size - 1) // chunk_size
        print(f"[청크 {chunk_num}/{total_chunks}] {', '.join(chunk_names)}")

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
            batch_id += 1

            if isinstance(result, Exception):
                print(f"  ✗ {name}: 실패 ({result})")
                canonical = {
                    "batch_id": batch_id,
                    "company_name": name,
                    "total_score": 0,
                    "verdict": "reject",
                    "criteria_scores": {},
                    "investment_memo": f"평가 실패: {result}",
                }
            else:
                canonical = _to_canonical(result, batch_id)
                total_score = canonical.get("total_score", 0)
                verdict = canonical.get("verdict", "N/A")
                print(f"  ✓ {name}: {verdict.upper()} ({total_score}/100)")

            _save_result(canonical, session_dir)

    t_end = time.time()

    # 5. 세션 메타 저장
    ablation_meta = {
        "session_id": session_id,
        "reference_session": meta["session_id"],
        "ablation_type": "rag_off",
        "started_at": datetime.now().isoformat(),
        "domain_fit": domain_fit,
        "elapsed_seconds": round(t_end - t_start, 1),
    }
    with open(os.path.join(session_dir, "session_meta.json"), "w", encoding="utf-8") as f:
        json.dump(ablation_meta, f, ensure_ascii=False, indent=2)

    # 6. 결과 비교
    print(f"\n{'=' * 60}")
    print("  Ablation 완료 — RAG ON vs RAG OFF 비교")
    print(f"{'=' * 60}")

    # 참조 세션 결과 로드
    ref_results = {}
    for fname in sorted(os.listdir(reference_session)):
        if fname.endswith(".json") and fname != "session_meta.json":
            with open(os.path.join(reference_session, fname), encoding="utf-8") as f:
                d = json.load(f)
                name = d.get("company_name", "")
                ref_results[name] = d

    # Ablation 결과 로드
    abl_results = {}
    for fname in sorted(os.listdir(session_dir)):
        if fname.endswith(".json") and fname != "session_meta.json":
            with open(os.path.join(session_dir, fname), encoding="utf-8") as f:
                d = json.load(f)
                name = d.get("company_name", "")
                abl_results[name] = d

    # 비교 테이블
    print(f"\n{'스타트업':<20} {'RAG ON':>8} {'RAG OFF':>8} {'차이':>6} {'방향일치':>8}")
    print("-" * 55)

    diffs = []
    for name in domain_fit:
        ref = ref_results.get(name, {})
        abl = abl_results.get(name, {})
        ref_score = ref.get("total_score", 0)
        abl_score = abl.get("total_score", 0)
        ref_verdict = ref.get("verdict", "?")
        abl_verdict = abl.get("verdict", "?")
        diff = ref_score - abl_score
        same_dir = "✓" if ref_verdict == abl_verdict else "✗"
        diffs.append(diff)
        print(f"  {name:<18} {ref_score:>6} {abl_score:>8} {diff:>+5} {same_dir:>8}")

    valid_diffs = [d for d in diffs if d != 0]
    if valid_diffs:
        avg_diff = sum(valid_diffs) / len(valid_diffs)
        print(f"\n  평균 점수 차이 (RAG ON - OFF): {avg_diff:+.1f}점")

    # 비교 결과 JSON 저장
    comparison = {
        "reference_session": meta["session_id"],
        "ablation_session": session_id,
        "comparison": [],
    }
    for name in domain_fit:
        ref = ref_results.get(name, {})
        abl = abl_results.get(name, {})
        comparison["comparison"].append({
            "startup": name,
            "rag_on_score": ref.get("total_score", 0),
            "rag_on_verdict": ref.get("verdict", "?"),
            "rag_off_score": abl.get("total_score", 0),
            "rag_off_verdict": abl.get("verdict", "?"),
            "score_diff": ref.get("total_score", 0) - abl.get("total_score", 0),
        })

    comp_path = os.path.join(session_dir, "ablation_comparison.json")
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(f"\n  비교 결과: {comp_path}")
    print(f"  소요 시간: {t_end - t_start:.1f}초")
    print("=" * 60)


def find_latest_session() -> str:
    """가장 최근 일반 배치 세션 찾기 (ablation 제외)."""
    sessions = sorted(
        [d for d in os.listdir(BATCH_RESULTS_DIR) if not d.startswith("ablation")],
        reverse=True,
    )
    if not sessions:
        print("ERROR: 참조할 배치 세션이 없습니다.")
        sys.exit(1)
    return os.path.join(BATCH_RESULTS_DIR, sessions[0])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        session = sys.argv[1]
    else:
        session = find_latest_session()

    run_ablation(session)
