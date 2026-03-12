"""RAGAS 기반 RAG 파이프라인 정량 평가 스크립트.

4대 메트릭 평가:
  - Faithfulness: 생성 응답이 검색된 컨텍스트에 근거하는지
  - ResponseRelevancy: 응답이 질문에 관련성 있는지
  - LLMContextPrecisionWithReference: 검색 문서의 정밀도
  - LLMContextRecall: 검색 문서가 정답을 충분히 커버하는지

사용법:
  .venv/bin/python evaluation/ragas_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics._answer_relevance import ResponseRelevancy
from ragas.metrics._context_precision import LLMContextPrecisionWithReference
from ragas.metrics._context_recall import LLMContextRecall
from ragas.metrics._faithfulness import Faithfulness

from config import LLM_MODEL, RAGAS_RESULTS_DIR
from rag.retriever import build_vectorstore, get_retriever


def load_test_dataset(path: str = "evaluation/test_dataset.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_answer(llm: ChatOpenAI, question: str, context: str) -> str:
    """RAG 컨텍스트를 기반으로 질문에 답변 생성."""
    prompt = f"""아래 참고 문서를 바탕으로 질문에 답변하세요. 문서에 없는 내용은 추측하지 마세요.

## 참고 문서
{context}

## 질문
{question}

## 답변 (한국어, 2-4문장)"""
    response = llm.invoke(prompt)
    return response.content


def run_ragas_evaluation():
    """RAGAS 평가 실행."""
    print("=" * 60)
    print("RAGAS RAG 파이프라인 평가")
    print("=" * 60)

    # 1. 벡터스토어 + 리트리버 로드
    print("\n[1/5] FAISS 벡터스토어 로드 중...")
    vectorstore = build_vectorstore(force_rebuild=False)
    retriever = get_retriever(vectorstore, k=5)

    if retriever is None:
        print("ERROR: 벡터스토어를 로드할 수 없습니다.")
        sys.exit(1)

    # 2. 테스트 데이터셋 로드
    print("[2/5] 테스트 데이터셋 로드 중...")
    test_data = load_test_dataset()
    print(f"  → {len(test_data)}개 질문 로드")

    # 3. 각 질문에 대해 RAG 검색 + 응답 생성
    print("[3/5] RAG 검색 + 응답 생성 중...")
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    samples: list[SingleTurnSample] = []
    retrieval_details: list[dict] = []

    for i, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"  [{i + 1}/{len(test_data)}] {question[:40]}...")

        # 검색
        docs = retriever.invoke(question)
        contexts = [doc.page_content for doc in docs]
        sources = [
            os.path.basename(doc.metadata.get("source", "unknown")) for doc in docs
        ]

        # 컨텍스트 포맷
        context_str = "\n\n".join(
            [f"[Doc {j + 1}] {ctx}" for j, ctx in enumerate(contexts)]
        )

        # 응답 생성
        answer = generate_answer(llm, question, context_str)

        # RAGAS 샘플 생성
        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=contexts,
            response=answer,
            reference=ground_truth,
        )
        samples.append(sample)

        retrieval_details.append(
            {
                "question": question,
                "query_type": item.get("query_type", "unknown"),
                "answer": answer,
                "ground_truth": ground_truth,
                "num_contexts": len(contexts),
                "sources": sources,
            }
        )

        # rate limit 방어
        time.sleep(1)

    # 4. RAGAS 평가 실행
    print("\n[4/5] RAGAS 메트릭 평가 중... (시간이 좀 걸립니다)")
    dataset = EvaluationDataset(samples=samples)

    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=LLM_MODEL, temperature=0))

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ResponseRelevancy(llm=evaluator_llm),
        LLMContextPrecisionWithReference(llm=evaluator_llm),
        LLMContextRecall(llm=evaluator_llm),
    ]

    result = evaluate(dataset=dataset, metrics=metrics)

    # 5. 결과 저장
    print("[5/5] 결과 저장 중...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(RAGAS_RESULTS_DIR, f"ragas_eval_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # 종합 점수
    summary = {
        "evaluation_date": timestamp,
        "num_questions": len(test_data),
        "metrics": {},
    }

    # result에서 메트릭 추출
    result_df = result.to_pandas()

    metric_names = [
        "faithfulness",
        "answer_relevancy",
        "llm_context_precision_with_reference",
        "context_recall",
    ]
    display_names = {
        "faithfulness": "Faithfulness (충실도)",
        "answer_relevancy": "Response Relevancy (응답 관련성)",
        "llm_context_precision_with_reference": "Context Precision (컨텍스트 정밀도)",
        "context_recall": "Context Recall (컨텍스트 재현율)",
    }

    print("\n" + "=" * 60)
    print("RAGAS 평가 결과")
    print("=" * 60)

    for metric_name in metric_names:
        if metric_name in result_df.columns:
            scores = result_df[metric_name].dropna().tolist()
            avg = sum(scores) / len(scores) if scores else 0
            summary["metrics"][metric_name] = {
                "display_name": display_names.get(metric_name, metric_name),
                "average": round(avg, 4),
                "scores": [round(s, 4) for s in scores],
            }
            print(f"  {display_names.get(metric_name, metric_name)}: {avg:.4f}")

    # 질문별 상세 결과
    per_question = []
    for i, detail in enumerate(retrieval_details):
        q_result = {**detail}
        for metric_name in metric_names:
            if metric_name in result_df.columns:
                q_result[metric_name] = round(
                    float(result_df.iloc[i][metric_name]), 4
                )
        per_question.append(q_result)

    summary["per_question"] = per_question

    # JSON 저장
    summary_path = os.path.join(output_dir, "ragas_results.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # CSV 저장
    csv_path = os.path.join(output_dir, "ragas_results.csv")
    result_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Markdown 리포트 생성
    report_path = os.path.join(output_dir, "ragas_report.md")
    _generate_report(summary, report_path)

    print(f"\n결과 저장 완료:")
    print(f"  JSON: {summary_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  Report: {report_path}")
    print("=" * 60)

    return summary


def _generate_report(summary: dict, output_path: str):
    """Markdown 형식의 RAGAS 평가 리포트 생성."""
    lines = []
    lines.append("# RAGAS RAG 파이프라인 평가 리포트\n")
    lines.append(f"**평가일**: {summary['evaluation_date']}")
    lines.append(f"**평가 질문 수**: {summary['num_questions']}개")
    lines.append(f"**RAG 구성**: Corrective RAG (FAISS + bge-m3 + GPT-4o-mini)")
    lines.append(f"**문서**: 4개 PDF → 174 청크\n")

    lines.append("---\n")
    lines.append("## 1. 종합 메트릭 점수\n")
    lines.append("| 메트릭 | 점수 | 설명 |")
    lines.append("|--------|------|------|")

    metric_descriptions = {
        "faithfulness": "생성 응답이 검색된 문서에 근거하는 정도",
        "answer_relevancy": "응답이 원래 질문에 관련성 있는 정도",
        "llm_context_precision_with_reference": "검색된 문서 중 실제 관련 문서의 비율",
        "context_recall": "정답에 필요한 정보를 검색 문서가 커버하는 정도",
    }

    for metric_name, info in summary["metrics"].items():
        score = info["average"]
        grade = "Excellent" if score >= 0.8 else "Good" if score >= 0.6 else "Fair" if score >= 0.4 else "Poor"
        desc = metric_descriptions.get(metric_name, "")
        lines.append(f"| {info['display_name']} | **{score:.4f}** ({grade}) | {desc} |")

    lines.append("\n---\n")
    lines.append("## 2. 질문별 상세 결과\n")
    lines.append(
        "| # | 질문 | 유형 | Faithfulness | Relevancy | Precision | Recall |"
    )
    lines.append("|---|------|------|-------------|-----------|-----------|--------|")

    for i, q in enumerate(summary.get("per_question", [])):
        short_q = q["question"][:30] + "..." if len(q["question"]) > 30 else q["question"]
        f_score = q.get("faithfulness", "-")
        r_score = q.get("answer_relevancy", "-")
        p_score = q.get("llm_context_precision_with_reference", "-")
        c_score = q.get("context_recall", "-")
        lines.append(
            f"| {i + 1} | {short_q} | {q['query_type']} | {f_score} | {r_score} | {p_score} | {c_score} |"
        )

    lines.append("\n---\n")
    lines.append("## 3. 메트릭 해석 가이드\n")
    lines.append("- **Faithfulness ≥ 0.8**: 응답이 검색 문서에 충실하게 근거함 (환각 최소)")
    lines.append("- **Response Relevancy ≥ 0.8**: 질문에 대해 적절한 답변을 생성")
    lines.append("- **Context Precision ≥ 0.7**: 검색된 문서 대부분이 실제로 관련 있음")
    lines.append("- **Context Recall ≥ 0.7**: 정답에 필요한 정보 대부분을 검색으로 확보")
    lines.append("")
    lines.append("## 4. RAG 파이프라인 구성\n")
    lines.append("```")
    lines.append("문서(4 PDF) → 청킹(1000자/200 overlap)")
    lines.append("  → FAISS 인덱싱(bge-m3 임베딩)")
    lines.append("  → Corrective RAG:")
    lines.append("      1) Top-5 검색")
    lines.append("      2) LLM 기반 관련성 평가 (binary yes/no)")
    lines.append("      3) 관련 문서 0개 → 쿼리 리라이트 → 재검색")
    lines.append("      4) 여전히 0개 → 웹 검색 fallback")
    lines.append("  → 에이전트 프롬프트에 컨텍스트 주입")
    lines.append("```")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_ragas_evaluation()
