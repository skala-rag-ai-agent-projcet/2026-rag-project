# AI Startup Investment Evaluation Agent

본 프로젝트는 **에너지 전환(Energy Transition)** 도메인의 스타트업에 대한 투자 가능성을 자동으로 평가하는 **Multi-Agent 시스템**을 설계하고 구현한 프로젝트입니다.

## Overview

| | |
|---|---|
| **Objective** | 에너지(배터리·ESS) 스타트업의 기술력, 시장성, 리스크 등 9개 기준으로 투자 적합성 자동 분석 |
| **Method** | Multi-Agent Workflow + Corrective RAG + Web Search |
| **Domain** | Energy Transition / Next-Gen Energy Infrastructure (배터리·ESS 중심) |
| **Threshold** | 100점 만점 중 60점 이상 시 Invest 판정 |

## Features

- **Corrective RAG 기반 근거 수집** — 4개 도메인 PDF(산업 개관, 기술 벤치마크, 정책·규제, SK 전략) → FAISS 벡터 검색 → LLM 관련성 평가 → 쿼리 리라이트/웹 검색 폴백
- **9개 투자 기준 정량 평가** — SK 시너지, 시장 규모, 기술 차별성, 팀 역량 등 가중합 100점 체계
- **배치 모드** — 웹 검색 기반 스타트업 자동 발굴 → 도메인 필터링 → 병렬 평가 → A4 요약 리포트
- **8페이지 투자 보고서 자동 생성** — Markdown → HTML → PDF 변환
- **점수 인플레이션 방지** — 역방향 웹 검색(리스크·약점 탐색) + 서버사이드 균일 점수 감점 로직

## Tech Stack

| Category | Details |
|----------|---------|
| **Orchestration** | LangGraph (StateGraph, 조건부 라우팅, 병렬 브랜치) |
| **LLM** | GPT-4o-mini via OpenAI API |
| **RAG** | FAISS + Corrective RAG (관련성 평가 → 쿼리 리라이트 → 웹 폴백) |
| **Embedding** | BAAI/bge-m3 (multilingual, 8192 토큰) |
| **Web Search** | Tavily Search API |
| **PDF Generation** | WeasyPrint (HTML → PDF) |
| **UI** | Streamlit |
| **Language** | Python 3.12 |

## Agents

본 시스템은 7개의 전문 에이전트가 파이프라인으로 연결됩니다.

| Agent | 역할 | RAG | 주요 입출력 |
|-------|------|-----|------------|
| **Startup Search** | 웹 검색으로 기업 프로필 수집 | - | → 기업명, 핵심기술, 펀딩 단계, 설립연도 |
| **Domain Check** | 에너지 도메인 적합성 판별 (최대 2회 재시도) | - | → is_energy_domain, sub_domain |
| **Tech Analysis** | 기술 경쟁력·TRL·차별성 심층 분석 | Corrective RAG | → TRL, 벤치마크 비교, 기술 리스크 |
| **Market & Policy** | 시장 규모(TAM/SAM)·정책·규제 분석 | Corrective RAG | → TAM, CAGR, 정책 수혜/리스크 |
| **Competitor Analysis** | 경쟁 환경 매핑 | - | → 경쟁사, 포지셔닝, 위협 수준 |
| **Investment Decision** | 9개 기준 가중 평가 + 투자 판정 | - | → 항목별 점수, 총점, invest/reject |
| **Report Writer** | 8페이지 투자 보고서 생성 | - | → Markdown + PDF 보고서 |

## Architecture

<img width="2448" height="3764" alt="Graph 제출용" src="https://github.com/user-attachments/assets/47f5768d-fad6-4ae4-83aa-d42b2462adcd" />


## Evaluation Criteria

9개 투자 평가 기준 (가중합 = 100점):

| # | 기준 | 배점 | 출처 | 핵심 질문 |
|---|------|------|------|----------|
| 1 | SK 사업 시너지 | 15점 | SK 전략자료 커스텀 | SK 에너지 밸류체인과 직접 연결되는가? |
| 2 | 시장 규모·성장성 | 17점 | Bessemer + Scorecard | TAM/SAM 규모와 성장 전망은? |
| 3 | 기술 차별성·상용화 | 14점 | Bessemer + Scorecard | 경쟁사 대비 차별적이고 상용화에 근접? |
| 4 | 창업자·팀 역량 | 12점 | Bessemer + Scorecard | 성공시킬 역량과 몰입도를 갖추었는가? |
| 5 | 문제 해결력 | 10점 | Bessemer Checklist | 고객 pain point가 명확하고 시급한가? |
| 6 | 확장성 | 10점 | Bessemer Checklist | 지역/산업 확장이 가능한 구조인가? |
| 7 | 고객 지불 의사 | 8점 | Bessemer Checklist | 실제 비용 지불 의사가 확인되는가? |
| 8 | 수익모델·단위경제성 | 8점 | Bessemer + VC 실사 | 수익 구조가 명확하고 검증되었는가? |
| 9 | 규제·운영 리스크 | 6점 | Bessemer Checklist | 규제·운영 리스크가 치명적인가? |

## RAG Pipeline

### Corrective RAG 구조

```
질의 → FAISS Top-5 검색 (bge-m3)
        → LLM 관련성 평가 (binary yes/no)
        → 관련 문서 50%+ → 컨텍스트 사용
        → 관련 문서 50%- → 쿼리 리라이트 → 재검색
        → 여전히 부족    → 웹 검색 폴백 (Tavily)
```

<img width="2804" height="1704" alt="CRAG 파이프라인" src="https://github.com/user-attachments/assets/4f576313-2b62-4057-9900-21f2dfb607f9" />


### RAG 문서 (4개 PDF → 174 청크)

| 문서 | 내용 |
|------|------|
| 배터리·에너지저장 산업 개관 | 시장 규모, 밸류체인, 수요처 구조, 중국 편중 리스크 |
| 에너지 저장 기술 벤치마크 | Li-ion/VRFB/NaS 등 기술별 TRL, RTE, 사이클 수명, LCOS 비교 |
| 한국 배터리·에너지 정책·규제 | K-배터리 정책, NDC, 배출권거래제, ESS 안전기준 |
| SK 전략 적합도 | SK 에너지 밸류체인, 시너지 평가 프레임워크 |

## Evaluation & Validation

RAG 파이프라인의 품질과 에이전트 의사결정의 유효성을 두 가지 방법으로 검증했습니다.

### 1. RAGAS 프레임워크 평가 — RAG 파이프라인 품질

15개 도메인 질문(시장/정책 7개, 기술 분석 8개)에 대해 [RAGAS](https://docs.ragas.io/) 4대 메트릭을 측정했습니다.

| Metric | Score | 의미 |
|--------|-------|------|
| **Faithfulness** (충실도) | **0.9611** | 응답이 검색 문서에 근거하는 정도 (환각 최소) |
| **Response Relevancy** (응답 관련성) | **0.8371** | 응답이 질문에 적절한 정도 |
| **Context Precision** (컨텍스트 정밀도) | **0.9869** | 검색된 문서 중 실제 관련 문서 비율 |
| **Context Recall** (컨텍스트 재현율) | **1.0000** | 정답에 필요한 정보를 검색이 커버하는 정도 |

- Context Recall 1.0 — 필요한 정보를 빠짐없이 검색
- Faithfulness 0.96 — LLM이 검색된 문서에 충실하게 답변 (환각 최소화)
- Context Precision 0.99 — 검색 결과 대부분이 실제로 관련 있는 문서

<img width="921" height="430" alt="스크린샷 2026-03-13 오전 9 06 02" src="https://github.com/user-attachments/assets/950e06ce-e0bb-4803-915d-a4832aba50cd" />

<img width="873" height="234" alt="스크린샷 2026-03-13 오전 9 05 13" src="https://github.com/user-attachments/assets/3d985963-a6e0-4f64-8779-b4bc5969f58e" />


### 2. Ablation Study — RAG가 에이전트 판단에 미치는 영향

동일한 10개 스타트업을 RAG ON/OFF 조건에서 평가하여 비교했습니다.

| | RAG ON | RAG OFF |
|---|---|---|
| **평균 점수** | 52.2점 | 53.9점 |
| **점수 범위** | 42 ~ 61점 | 49 ~ 58점 |
| **Invest 판정** | **1개** (스탠다드에너지) | 0개 |
| **점수 표준편차** | 높음 (변별력 ↑) | 낮음 (균일, 변별력 ↓) |

**핵심 발견:**
- **RAG OFF**는 모든 스타트업에 비슷한 점수(49~58)를 부여 → 변별력 없음
- **RAG ON**은 도메인 벤치마크 대비 검증이 가능하여 점수 범위가 넓어짐(42~61)
- 스탠다드에너지(VRFB, TRL 6-8)만 유일하게 invest 판정 → RAG 문서의 기술 벤치마크가 정당한 가점의 근거로 작용
- RAG = "점수를 높이는 도구"가 아니라 **"변별력을 만드는 도구"**

<img width="2798" height="2337" alt="ablation_comparison_detailed" src="https://github.com/user-attachments/assets/60556d34-d8b8-4939-b834-336e3bb5154b" />


## Directory Structure

```
ai-startup-investment-agent/
├── app.py                       # CLI 엔트리포인트 (Single / Batch)
├── config.py                    # 설정 (모델, 평가기준 9개, 배치 파라미터)
├── streamlit_app.py             # Streamlit Web UI
├── agents/                      # 에이전트 모듈 (7+4 batch)
│   ├── startup_search.py        #   스타트업 프로필 수집
│   ├── domain_check.py          #   에너지 도메인 판별
│   ├── tech_analysis.py         #   기술 분석 (CRAG)
│   ├── market_policy.py         #   시장·정책 분석 (CRAG)
│   ├── competitor_analysis.py   #   경쟁사 분석
│   ├── investment_decision.py   #   9개 기준 투자 판단
│   ├── evaluation_check.py      #   평가 검증
│   ├── report_writer.py         #   8페이지 보고서 생성
│   └── batch_*.py               #   배치 전용 에이전트 (4개)
├── graph/                       # LangGraph 워크플로우
│   ├── state.py                 #   GraphState 정의
│   ├── workflow.py              #   단일 모드 그래프
│   └── batch_workflow.py        #   배치 모드 그래프
├── rag/                         # RAG 파이프라인
│   ├── retriever.py             #   FAISS 벡터스토어 빌더
│   └── corrective_rag.py        #   Corrective RAG 구현
├── prompts/                     # 프롬프트 템플릿
│   ├── templates.py             #   단일 모드 프롬프트 (495줄)
│   └── batch_templates.py       #   배치 모드 프롬프트
├── tools/
│   └── search.py                # Tavily 웹 검색 래퍼
├── data/                        # RAG 문서 + FAISS 인덱스
│   ├── faiss_index/             #   사전 빌드된 벡터 인덱스
│   └── *.pdf                    #   도메인 문서 4개
├── evaluation/                  # 평가 스크립트
│   ├── ragas_eval.py            #   RAGAS 4대 메트릭 평가
│   ├── test_dataset.json        #   15개 테스트 질문
│   ├── ablation_rag_off.py      #   Ablation Study 실행
│   └── ablation_visualize.py    #   Ablation 시각화
├── docs/                        # 설계 문서 + 다이어그램
├── outputs/                     # 전체 결과 디렉토리
│   ├── single_results/          #   개별 스타트업 투자 보고서 (MD+PDF)
│   ├── batch_results/           #   배치 세션 결과 + 서머리 리포트
│   ├── ragas_results/           #   RAGAS 평가 결과
│   └── ablation_results/        #   Ablation Study 차트
└── requirements.txt
```

## Contributors

| 양정우 (PM) <br> [@mrangjw](https://github.com/mrangjw) | 박지현 <br> [@pjhyun0225](https://github.com/pjhyun0225) | 정재환 <br> [@hwnnn](https://github.com/hwnnn) | 이채연 <br> [@coduslee](https://github.com/coduslee) |
|:---:|:---:|:---:|:---:|
| <img width="150" src="https://avatars.githubusercontent.com/u/157506327?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/82721608?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/169510824?v=4"/> | <img width="150" src="https://avatars.githubusercontent.com/u/260080132?v=4"/> |
| 스타트업 탐색 에이전트<br>투자 판단 에이전트<br>Corrective RAG 파이프라인<br>평가 검증 (RAGAS + Ablation) | 기술 분석 에이전트<br>투자 보고서 생성 에이전트 | 시장·정책 분석 에이전트<br>도메인 체크 에이전트<br>프롬프트 엔지니어링 | 경쟁사 분석 에이전트<br>도메인 데이터 큐레이션 (PDF 4종)<br>Streamlit UI |
