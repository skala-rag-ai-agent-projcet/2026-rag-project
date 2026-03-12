"""Corrective RAG — 문서 관련성 평가 + 쿼리 리라이트 + 웹 보완."""

from __future__ import annotations

import os
from typing import Sequence

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import LLM_MODEL
from tools.search import web_search


# ── Structured Output ────────────────────────────────────────────────
class GradeDocuments(BaseModel):
    """Retrieved document relevance check (binary yes/no)."""

    binary_score: str = Field(
        description="Document is relevant to the question: 'yes' or 'no'"
    )


# ── Builder helpers ──────────────────────────────────────────────────
def _build_retrieval_grader():
    """LLM grader: 문서가 쿼리와 관련 있는지 yes/no 판별."""
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    structured_llm = llm.with_structured_output(GradeDocuments)

    grade_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a grader assessing relevance of a retrieved document "
                "to a user question.\n"
                "If the document contains keyword(s) or semantic meaning related "
                "to the question, grade it as relevant.\n"
                "Give a binary score 'yes' or 'no' to indicate whether the "
                "document is relevant to the question.",
            ),
            (
                "human",
                "Retrieved document:\n\n{document}\n\n"
                "User question: {question}\n",
            ),
        ]
    )
    return grade_prompt | structured_llm


def _build_question_rewriter():
    """쿼리 리라이터: 관련 문서가 없을 때 쿼리를 개선."""
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a question re-writer that converts an input question "
                "to a better version optimized for vectorstore retrieval and "
                "web search. Look at the input and try to reason about the "
                "underlying semantic intent / meaning. "
                "Output ONLY the improved question in the same language as input.",
            ),
            ("human", "Here is the initial question:\n\n{question}\n"),
        ]
    )
    return re_write_prompt | llm | StrOutputParser()


# ── Main entry point ─────────────────────────────────────────────────
def corrective_retrieve(
    retriever,
    query: str,
    startup_name: str,
) -> tuple[str, list[str], list[str]]:
    """Corrective RAG: retrieve → grade → (rewrite + web fallback) → format.

    Returns:
        (context_str, sources_list, log_list)
    """
    log: list[str] = []
    sources: list[str] = []

    # ── 0. retriever 없으면 바로 웹 검색 ──
    if retriever is None:
        log.append(f"[CRAG] {startup_name}: retriever 없음 → 웹 검색 fallback")
        web_results = web_search(query, max_results=5)
        sources.append(f"CRAG 웹 fallback: {startup_name}")
        return web_results, sources, log

    # ── 1. Retrieve top-k docs ──
    docs: list[Document] = retriever.invoke(query)
    log.append(f"[CRAG] {startup_name}: {len(docs)}개 문서 검색됨")

    # ── 2. Grade each document ──
    grader = _build_retrieval_grader()
    relevant_docs: list[Document] = []

    for doc in docs:
        grade: GradeDocuments = grader.invoke(
            {"document": doc.page_content, "question": query}
        )
        if grade.binary_score == "yes":
            relevant_docs.append(doc)

    log.append(
        f"[CRAG] {startup_name}: {len(relevant_docs)}/{len(docs)}개 관련 문서 통과"
    )

    # ── 3. 관련 문서 0개 → 쿼리 리라이트 + 웹 검색 보완 ──
    if not relevant_docs:
        log.append(f"[CRAG] {startup_name}: 관련 문서 없음 → 쿼리 리라이트 + 웹 검색")

        rewriter = _build_question_rewriter()
        improved_query = rewriter.invoke({"question": query})
        log.append(f"[CRAG] 리라이트 쿼리: {improved_query}")

        # 리라이트된 쿼리로 재검색
        retry_docs = retriever.invoke(improved_query)
        for doc in retry_docs:
            grade = grader.invoke(
                {"document": doc.page_content, "question": improved_query}
            )
            if grade.binary_score == "yes":
                relevant_docs.append(doc)

        log.append(
            f"[CRAG] {startup_name}: 리라이트 후 {len(relevant_docs)}개 관련 문서"
        )

        # 여전히 0개면 웹 검색으로 보완
        if not relevant_docs:
            web_results = web_search(improved_query, max_results=5)
            sources.append(f"CRAG 웹 보완 검색: {startup_name}")
            log.append(f"[CRAG] {startup_name}: 웹 검색으로 보완")
            return web_results, sources, log

    # ── 4. 필터링된 docs → retrieve_context 형식으로 포맷 ──
    context_parts: list[str] = []
    for i, doc in enumerate(relevant_docs, 1):
        source = doc.metadata.get("source", "unknown")
        basename = os.path.basename(source)
        context_parts.append(
            f"[Document {i}] (Source: {basename})\n{doc.page_content}"
        )
        sources.append(f"RAG: {basename}")

    return "\n\n".join(context_parts), sources, log
